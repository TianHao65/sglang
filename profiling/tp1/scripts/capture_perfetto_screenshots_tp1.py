"""Capture native Perfetto selections from complete unmodified paired TP1 traces."""
import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/tp1"
(EVIDENCE / "figures").mkdir(parents=True, exist_ok=True)
(EVIDENCE / "capture").mkdir(exist_ok=True)
records = json.loads((ROOT / "review/selection-manifest-tp1.json").read_text())
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        env=dict(os.environ, LD_LIBRARY_PATH=str(ROOT / "review/browser_libs/usr/lib64")),
        args=["--no-sandbox"],
    )
    for record in records:
        source = Path(record["source"])
        raw = source.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record["source_sha256"]
        page = browser.new_page(viewport={"width": 2800, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        for attempt in range(3):
            try:
                page.goto("https://ui.perfetto.dev", wait_until="commit", timeout=45000)
                page.get_by_text("Open trace file", exact=False).first.wait_for(timeout=45000)
                break
            except Exception:
                if attempt == 2:
                    raise
        with page.expect_file_chooser() as chooser:
            page.get_by_text("Open trace file", exact=False).first.click()
        chooser.value.set_files(str(source))
        page.wait_for_function("typeof ctx !== 'undefined' && ctx?.tracks?.getAllTracks().length > 0", timeout=45000)
        page.wait_for_timeout(800)
        try:
            page.get_by_role("button", name="OK", exact=True).click(timeout=1000)
        except Exception:
            pass
        result = page.evaluate("""async (r) => {
            const s = r.selected;
            const q = await ctx.engine.query(`select id,ts,dur,track_id,name from slice where ts between ${BigInt(s.ts_ns)-2n} and ${BigInt(s.ts_ns)+2n}`);
            const rows=[];
            for (const it=q.iter({});it.valid();it.next()) if(it.name === s.name) rows.push({id:Number(it.id),ts:Number(it.ts),dur:Number(it.dur),track_id:Number(it.track_id),name:it.name});
            if(rows.length !== 1) throw new Error('Original operator missing or ambiguous');
            const row=rows[0];
            const track=ctx.tracks.getAllTracks().find(t => t.tags?.kinds?.includes('SliceTrack') && t.tags.trackIds?.includes(row.track_id));
            if(!track) throw new Error('Original GPU track missing');
            const node=ctx.workspaces.currentWorkspace.getTrackByUri(track.uri);
            node.reveal();node.expand();
            app.settings.get('theme').set('dark');
            const width=r.window_width_ns;
            const windowStart=row.ts-(r.phase==='prefill'?20000:8000),windowEnd=windowStart+width;
            ctx.timeline.setVisibleWindow(ctx.timeline.visibleWindow.constructor.fromTime(BigInt(windowStart),BigInt(windowEnd)));
            ctx.selection.selectArea({start:BigInt(row.ts),end:BigInt(row.ts+row.dur),trackUris:[track.uri]},{switchToCurrentSelectionTab:true});
            ctx.selection.setCurrentSelectionSubTab('slice_aggregation');
            ctx.tabs.showCurrentSelectionTab();ctx.tabs.setTabPanelVisibility(0);
            raf.scheduleCanvasRedraw();
            const diagnostics=await ctx.engine.query("select name,value from stats where severity='error' and value>0");
            const importErrors=[];for(const it=diagnostics.iter({});it.valid();it.next()) importErrors.push({name:it.name,value:Number(it.value)});
            const count=await ctx.engine.query('select count(*) as n from slice');
            return {row,track_uri:track.uri,track_tags:track.tags,window_start_ns:windowStart,window_end_ns:windowEnd,import_errors:importErrors,loaded_slice_count:Number(count.iter({}).n)};
        }""", record)
        assert abs(result["row"]["ts"] - int(record["selected"]["ts_ns"])) <= 1
        assert result["row"]["dur"] == int(record["selected"]["dur_ns"])
        page.get_by_text("Area Selection", exact=True).first.wait_for(timeout=15000)
        page.get_by_text("Wall Duration", exact=False).first.wait_for(timeout=15000)
        page.get_by_text(record["selected"]["name"], exact=True).first.wait_for(timeout=15000)
        page.wait_for_timeout(800)
        handle = page.locator(".pf-grid__resize-handle").first.bounding_box()
        if handle:
            page.mouse.move(handle["x"]+handle["width"]/2,handle["y"]+handle["height"]/2)
            page.mouse.down()
            page.mouse.move(1720,handle["y"]+handle["height"]/2,steps=12)
            page.mouse.up()
        page.wait_for_timeout(500)
        page.mouse.move(650,20)
        screenshot = f"figures/{record['phase']}-{record['side']}.png"
        page.screenshot(path=str(EVIDENCE / screenshot))
        body = page.locator("body").inner_text()
        result.update(record=record,screenshot=screenshot,page_errors=errors,
            original_bytes_unchanged=source.read_bytes()==raw,
            native_area=page.evaluate("ctx.selection.selection.kind === 'area'"),
            native_slices=page.evaluate("ctx.selection.currentSelectionSubTab === 'slice_aggregation'"),
            kernel_name_in_native_list=record["selected"]["name"] in body,
            native_selection_text=body[body.index("Area Selection"):])
        (EVIDENCE / f"capture/{record['phase']}-{record['side']}.json").write_text(json.dumps(result,indent=2)+"\n")
        assert result["original_bytes_unchanged"] and result["native_area"] and result["native_slices"] and result["kernel_name_in_native_list"] and not errors
        print(f"Captured {record['phase']} {record['side']}: complete original trace, native selection",flush=True)
        page.close()
    browser.close()
