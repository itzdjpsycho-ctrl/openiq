import os,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8000/')
    page.get_by_label('Username:').fill('demo');page.get_by_label('Password:').fill(os.getenv('DEMO_PASSWORD','prototype-local-2026'));page.get_by_role('button',name='Sign in',exact=True).click()
    page.wait_for_selector('.card')
    for name in ['Members','History','Analytics','My Stats','Performance','Signups','Gear','Live War','Alliance','Streams','Community','Settings']:
        page.locator('nav').get_by_role('button',name=name,exact=True).click()
        page.wait_for_timeout(100)
        assert page.locator('#title').inner_text()==name
        assert not page.locator('#error').is_visible(),page.locator('#error').inner_text()
    page.locator('nav').get_by_role('button',name='Members',exact=True).click()
    page.get_by_role('button',name='Add member',exact=True).click()
    test_name=test_name+uuid.uuid4().hex[:6]
    page.get_by_label('Family name',exact=True).fill(test_name)
    page.get_by_role('button',name='Save',exact=True).click()
    page.wait_for_function('!document.querySelector("#dialog").open')
    page.get_by_placeholder('Search family name…').fill(test_name)
    assert page.locator('#panel').get_by_role('heading',name=test_name).count()==1
    page.get_by_placeholder('Search family name…').fill('')
    page.evaluate("async n => { const m=state.records.member.find(m=>m.name===n); await call('roster','remove',{member:m.id}); }",test_name)
    page.screenshot(path='docs/dashboard.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='docs/mobile.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile page overflows horizontally'
    assert not errors,errors
    print('Browser smoke passed: 12 tabs, member creation, search, responsive layout, no JavaScript errors.')
    browser.close()
