"""Capture native Perfetto views of complete unchanged original model traces."""
import hashlib
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / 'metadata/stage-manifest.json').read_text())
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/tmp/perfetto-playwright-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell', args=['--no-sandbox'])
    for row in rows:
        if os.environ.get('ONLY') and os.environ['ONLY'] != row['stage'] + '-' + row['side']:
            continue
        source = Path(row['source'])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == row['source_sha256']
        selected = row['selected'][0]
        page = browser.new_page(viewport={'width':2400,'height':1000},device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('https://ui.perfetto.dev', wait_until='domcontentloaded', timeout=60000)
        with page.expect_file_chooser() as chooser:
            page.get_by_text('Open trace file', exact=False).first.click()
        chooser.value.set_files(str(source))
        page.wait_for_function("typeof ctx!=='undefined' && ctx?.tracks?.getAllTracks().length>0", timeout=60000)
        try: page.get_by_role('button',name='OK',exact=True).click(timeout=1000)
        except Exception: pass
        data = page.evaluate('''async (r)=>{
            const selected=r.selected[0];
            const q=await ctx.engine.query(`select id,ts,dur,track_id,name from slice where ts between ${selected.ts_ns-2} and ${selected.ts_ns+2}`);
            const slices=[];for(const it=q.iter({});it.valid();it.next())if(it.name===selected.name)slices.push({id:Number(it.id),ts:Number(it.ts),dur:Number(it.dur),track_id:Number(it.track_id),name:it.name});
            if(slices.length!==1)throw new Error('Expected one original affected kernel');
            const s=slices[0];const track=ctx.tracks.getAllTracks().find(t=>t.tags?.kinds?.includes('SliceTrack') && t.tags.trackIds?.includes(s.track_id));
            if(!track)throw new Error('Original GPU stream is unavailable');
            const node=ctx.workspaces.currentWorkspace.getTrackByUri(track.uri);node.reveal();node.expand();
            app.settings.get('theme').set('dark');
            const start=s.ts,end=s.ts+s.dur,windowStart=start-(r.stage==='prefill'?20000:8000),windowEnd=windowStart+r.window_width_ns;
            ctx.timeline.setVisibleWindow(ctx.timeline.visibleWindow.constructor.fromTime(BigInt(windowStart),BigInt(windowEnd)));
            ctx.selection.selectArea({start:BigInt(start),end:BigInt(end),trackUris:[track.uri]},{switchToCurrentSelectionTab:true});
            ctx.selection.setCurrentSelectionSubTab('slice_aggregation');ctx.tabs.showCurrentSelectionTab();ctx.tabs.setTabPanelVisibility(0);
            raf.scheduleCanvasRedraw();
            const count=await ctx.engine.query('select count(*) as n from slice');
            const diagnostic=await ctx.engine.query("select name,value from stats where severity='error' and value>0");const importErrors=[];for(const it=diagnostic.iter({});it.valid();it.next())importErrors.push({name:it.name,value:Number(it.value)});
            return {slice:s,track_uri:track.uri,track_tags:track.tags,start_ns:start,end_ns:end,window_start_ns:windowStart,window_end_ns:windowEnd,loaded_slice_count:Number(count.iter({}).n),importErrors};
        }''',row)
        assert abs(data['slice']['ts'] - selected['ts_ns']) <= 1
        assert data['slice']['dur'] == selected['dur_ns']
        page.get_by_text('Area Selection',exact=True).first.wait_for(timeout=20000)
        page.get_by_text('Wall Duration',exact=False).first.wait_for(timeout=20000)
        page.get_by_text(selected['name'],exact=True).first.wait_for(timeout=20000)
        page.wait_for_timeout(1200)
        handle=page.locator('.pf-grid__resize-handle').first.bounding_box()
        if handle:
            page.mouse.move(handle['x']+handle['width']/2,handle['y']+handle['height']/2);page.mouse.down();page.mouse.move(1600,handle['y']+handle['height']/2,steps=12);page.mouse.up()
        page.wait_for_timeout(700);page.mouse.move(650,20);page.wait_for_timeout(300)
        image=f"figures/{row['stage']}-{row['side']}-original-perfetto.png"
        page.screenshot(path=str(ROOT/image))
        body=page.locator('body').inner_text()
        record={**row,**data,'screenshot':image,'native_area':page.evaluate("ctx.selection.selection.kind==='area'"),'native_slices':page.evaluate("ctx.selection.currentSelectionSubTab==='slice_aggregation'"),'kernel_in_native_list':selected['name'] in body,'page_errors':errors,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==row['source_sha256'],'native_list_text':body[body.index('Area Selection'):]}
        (ROOT/'metadata'/f"{row['stage']}-{row['side']}-capture.json").write_text(json.dumps(record,indent=2)+'\n')
        assert record['native_area'] and record['native_slices'] and record['kernel_in_native_list'] and record['source_unchanged'] and not errors
        print(row['stage'],row['side'],'captured complete original trace',data['loaded_slice_count'],flush=True)
        page.close()
    browser.close()
