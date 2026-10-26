"""Open complete, byte-identical original traces; change only native UI state."""
import gzip,hashlib,json,os
from decimal import Decimal
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
old=R.parent/'perfetto_screenshots_20261022'
records=json.loads((old/'results/stage-manifest.json').read_text())
checks=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/tmp/perfetto-playwright-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell',args=['--no-sandbox'])
 for r in records:
  if os.environ.get('ONLY') and os.environ['ONLY']!=r['stage']+'-'+r['mode']:continue
  source=Path(r['source']);raw=source.read_bytes()
  assert hashlib.sha256(raw).hexdigest()==r['source_sha256']
  original=json.loads(gzip.decompress(raw),parse_float=Decimal)
  events=original['traceEvents']
  selected=[]
  for s in r['selected']:
   matches=[e for e in events if e.get('ph')=='X' and e.get('name')==s['kernel'] and abs(Decimal(str(e['ts']))-Decimal(str(s['source_timestamp_us'])))<Decimal('.001')]
   assert len(matches)==1
   e=matches[0]
   selected.append({'name':e['name'],'source_ts_us':str(e['ts']),'source_dur_us':str(e['dur']),'ts_ns':int(e['ts']*1000),'dur_ns':int(e['dur']*1000),'pid':e['pid'],'tid':e['tid'],'stream':e['args'].get('stream')})
  p=b.new_page(viewport={'width':2400,'height':840},device_scale_factor=1)
  errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  p.goto('https://ui.perfetto.dev',wait_until='domcontentloaded',timeout=45000)
  with p.expect_file_chooser() as fc:p.get_by_text('Open trace file',exact=False).first.click()
  fc.value.set_files(str(source))
  p.wait_for_function("typeof ctx!=='undefined' && ctx?.tracks?.getAllTracks().length>0",timeout=45000)
  p.wait_for_timeout(1000)
  try:p.get_by_role('button',name='OK',exact=True).click(timeout=1000)
  except Exception:pass
  data=p.evaluate("""async(r)=>{
   const rows=[];
   for(const s of r.selected){
    const q=await ctx.engine.query(`select id,ts,dur,track_id,name from slice where ts between ${s.ts_ns-2} and ${s.ts_ns+2}`);
    for(const it=q.iter({});it.valid();it.next())if(it.name===s.name)rows.push({id:Number(it.id),ts:Number(it.ts),dur:Number(it.dur),track_id:Number(it.track_id),name:it.name});
   }
   if(rows.length!==2)throw new Error('Original selected events missing');
   const track=ctx.tracks.getAllTracks().find(t=>t.tags?.kinds?.includes('SliceTrack') && rows.every(s=>t.tags.trackIds?.includes(s.track_id)));
   if(!track)throw new Error('Original GPU stream missing');
   const node=ctx.workspaces.currentWorkspace.getTrackByUri(track.uri);
   node.reveal();node.expand();
   app.settings.get('theme').set('dark');
   const start=rows[0].ts,end=rows[1].ts+rows[1].dur;
   const windowStart=start-(r.stage==='prefill'?20000:8000),windowEnd=windowStart+(r.stage==='prefill'?100000:40000);
   ctx.timeline.setVisibleWindow(ctx.timeline.visibleWindow.constructor.fromTime(BigInt(windowStart),BigInt(windowEnd)));
   ctx.selection.selectArea({start:BigInt(start),end:BigInt(end),trackUris:[track.uri]},{switchToCurrentSelectionTab:true});
   ctx.selection.setCurrentSelectionSubTab('slice_aggregation');ctx.tabs.showCurrentSelectionTab();ctx.tabs.setTabPanelVisibility(0);
   raf.scheduleCanvasRedraw();
   const stats=await ctx.engine.query("select name,value from stats where severity='error' and value>0");const importErrors=[];
   for(const it=stats.iter({});it.valid();it.next())importErrors.push({name:it.name,value:Number(it.value)});
   const count=await ctx.engine.query('select count(*) as n from slice');
   return {rows,track_uri:track.uri,track_tags:track.tags,start_ns:start,end_ns:end,window_start_ns:windowStart,window_end_ns:windowEnd,importErrors,loaded_slice_count:Number(count.iter({}).n)};
  }""",{'stage':r['stage'],'selected':selected})
  for i,e in enumerate(data['rows']):
   assert abs(e['ts']-selected[i]['ts_ns'])<=1
   assert e['dur']==selected[i]['dur_ns']
  p.get_by_text('Area Selection',exact=True).first.wait_for(timeout=20000)
  p.get_by_text('Wall Duration',exact=False).first.wait_for(timeout=20000)
  for s in selected:p.get_by_text(s['name'],exact=True).first.wait_for(timeout=20000)
  p.wait_for_timeout(1200)
  handle=p.locator('.pf-grid__resize-handle').first.bounding_box()
  if handle:
   p.mouse.move(handle['x']+handle['width']/2,handle['y']+handle['height']/2);p.mouse.down();p.mouse.move(1690,handle['y']+handle['height']/2,steps=12);p.mouse.up()
  p.wait_for_timeout(500)
  p.mouse.move(650,20)
  p.wait_for_timeout(300)
  name=f"pr8-{r['stage']}-{r['mode']}-original-perfetto.png"
  p.screenshot(path=str(R/'figures'/name))
  body=p.locator('body').inner_text()
  c={**data,'stage':r['stage'],'mode':r['mode'],'source':str(source),'source_sha256':r['source_sha256'],'source_bytes':len(raw),'source_event_count':len(events),'source_unchanged':source.read_bytes()==raw,'selected_original_events':selected,'screenshot':'figures/'+name,'native_area':p.evaluate("ctx.selection.selection.kind==='area'"),'native_slices':p.evaluate("ctx.selection.currentSelectionSubTab==='slice_aggregation'"),'kernel_names_in_native_list':all(s['name'] in body for s in selected),'stream_7_visible':'stream 7' in body,'page_errors':errors,'native_list_text':body[body.index('Area Selection'):]}
  checks.append(c)
  (R/'results'/f"{r['stage']}-{r['mode']}-check.json").write_text(json.dumps(c,indent=2)+'\n')
  (R/'results'/f"{r['stage']}-{r['mode']}-dom.html").write_text(p.content())
  print(r['stage'],r['mode'],'captured original full trace',data['track_uri'],data['loaded_slice_count'],flush=True)
  assert c['native_area'] and c['native_slices'] and c['kernel_names_in_native_list'] and c['stream_7_visible'] and c['source_unchanged'] and not errors
  p.close()
 b.close()
