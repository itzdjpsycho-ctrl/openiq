"""Exercise real browser workflows in an isolated, disposable local guild."""
import os,uuid
from playwright.sync_api import sync_playwright
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH','/tmp/critiq-browsers')
base=os.getenv('OPENIQ_URL','http://127.0.0.1:8765')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/')
    page.get_by_label('Username:').fill('demo');page.get_by_label('Password:').fill(os.getenv('DEMO_PASSWORD','prototype-local-2026'));page.get_by_role('button',name='Sign in',exact=True).click()
    page.wait_for_selector('.card')
    for name in ['Members','History','Analytics','My Stats','Performance','Signups','Gear','Live War','Alliance','Streams','Community','Settings']:
        page.locator('nav').get_by_role('button',name=name,exact=True).click()
        assert page.locator('#title').inner_text()==name
        assert not page.locator('#error').is_visible()
    page.locator('nav').get_by_role('button',name='Members',exact=True).click()
    assert page.title()=='OpenIQ'
    page.screenshot(path='docs/dashboard.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path='docs/mobile.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile overflow'
    page.set_viewport_size({'width':1440,'height':1000})
    test_guild='UITest-'+uuid.uuid4().hex[:8]
    created=page.evaluate('''async name => {
      const r=await fetch('/onboard/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({name,names:['TestAlpha','TestBeta']})});
      if(!r.ok)throw Error(await r.text());return await r.json();
    }''',test_guild)
    try:
        page.reload();page.wait_for_selector('#guild');page.locator('#guild').select_option(str(created['id']))
        page.wait_for_function('state && state.guild.id===Number(document.querySelector("#guild").value)')
        page.get_by_role('button',name='Add member',exact=True).click();page.get_by_label('Family name',exact=True).fill('TestGamma');page.get_by_role('button',name='Save',exact=True).click();page.wait_for_function('!document.querySelector("#dialog").open || document.querySelector("#form-error").textContent');assert not page.locator('#dialog').is_visible(), page.locator('#form-error').inner_text()
        page.get_by_placeholder('Search family name…').fill('TestGamma');assert page.locator('#panel').get_by_role('heading',name='TestGamma').count()==1
        page.get_by_placeholder('Search family name…').fill('')
        page.locator('nav').get_by_role('button',name='History',exact=True).click()
        page.locator('.actions-menu').select_option(label='Record war')
        page.get_by_label('Kills',exact=True).fill('20');page.get_by_label('Deaths',exact=True).fill('4');page.get_by_label('War class',exact=True).fill('Warrior')
        page.get_by_role('button',name='Save',exact=True).click();page.wait_for_function('!document.querySelector("#dialog").open || document.querySelector("#form-error").textContent');assert not page.locator('#dialog').is_visible(), page.locator('#form-error').inner_text()
        assert page.locator('#panel td').filter(has_text='20').count()>0
        page.locator('nav').get_by_role('button',name='Signups',exact=True).click();page.get_by_role('button',name='Create event',exact=True).click();page.get_by_label('Title',exact=True).fill('UI test event');page.get_by_role('button',name='Save',exact=True).click();page.wait_for_function('!document.querySelector("#dialog").open || document.querySelector("#form-error").textContent');assert not page.locator('#dialog').is_visible(), page.locator('#form-error').inner_text()
        assert page.get_by_role('heading',name='UI test event',exact=True).count()==1
        page.locator('nav').get_by_role('button',name='Gear',exact=True).click();page.get_by_role('button',name='Update gear',exact=True).click()
        for label,value in [('AP','300'),('Awakening AP','302'),('DP','400')]:page.get_by_label(label,exact=True).fill(value)
        page.get_by_role('button',name='Save',exact=True).click();page.wait_for_function('!document.querySelector("#dialog").open || document.querySelector("#form-error").textContent');assert not page.locator('#dialog').is_visible(), page.locator('#form-error').inner_text();assert page.locator('#panel strong').filter(has_text='702').count()==1
        parsed=page.evaluate("async()=>await parseIkusaText('[23:59:58] Alpha has killed Enemy from Rival\\n[00:00:02] Alpha died to Enemy from Rival','2026-09-11','+12:00')")
        assert len(parsed)==2 and parsed[1]['player']=='Enemy'
        assert not errors,errors
        print('Browser passed: OpenIQ branding, 12 tabs, mobile layout, member search/create, war entry, event creation, gear update, browser IKUSA parsing, no JavaScript errors.')
    except Exception:
        print('FORM ERROR:',page.locator('#form-error').inner_text())
        print('INVALID:',page.evaluate('Array.from(document.querySelectorAll("#action-form :invalid")).map(e=>({tag:e.tagName,type:e.type,value:e.value,message:e.validationMessage}))'))
        print('JS ERRORS:',errors)
        raise
    finally:
        page.evaluate('''async ({id,name})=>{const r=await fetch(`/api/${id}/admin/disband/`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},body:JSON.stringify({confirmation:name})});if(!r.ok)throw Error(await r.text());}''',{'id':created['id'],'name':test_guild})
        browser.close()
