"""Opt-in shared dashboard UX checks: OPENIQ_BROWSER_TEST=1."""
import os
from unittest import skipUnless

from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from .models import Access, Guild


@skipUnless(os.getenv('OPENIQ_BROWSER_TEST') == '1', 'Opt-in browser integration')
@override_settings(DEBUG=True, SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class DashboardUXTests(StaticLiveServerTestCase):
    def test_empty_states_keyboard_and_failed_save(self):
        from playwright.sync_api import sync_playwright

        user = User.objects.create_user('ux-test')
        guild = Guild.objects.create(name='Empty UX guild')
        Access.objects.create(user=user, guild=guild, role='owner')
        self.client.force_login(user)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            try:
                page = browser.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce')
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.context.add_cookies([{'name': 'sessionid', 'value': self.client.cookies['sessionid'].value, 'url': self.live_server_url}])
                page.goto(self.live_server_url)
                history = page.get_by_role('button', name='History', exact=True)
                history.focus()
                page.keyboard.press('Enter')
                self.assertEqual(page.locator('#nav [aria-current="page"]').inner_text(), 'History')
                self.assertEqual(page.evaluate('document.activeElement.textContent'), 'History')
                self.assertGreater(page.get_by_text('No records to show.', exact=False).count(), 0)
                self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                page.get_by_role('button', name='Members', exact=True).click()
                page.get_by_role('button', name='Add member', exact=True).click()
                self.assertEqual(page.get_by_role('dialog').get_attribute('aria-labelledby'), 'dialog-title')
                field = page.get_by_label('Family name', exact=True)
                field.fill('KeepMyInput')
                # A delayed rejection lets us exercise keyboard dismissal and duplicate submit guards.
                page.evaluate("""() => {
                    window.uxCalls = 0;
                    activeAction.custom = () => {
                        window.uxCalls++;
                        return new Promise((resolve, reject) => { window.uxReject = reject; });
                    };
                }""")
                page.get_by_role('button', name='Save', exact=True).click()
                self.assertTrue(page.get_by_role('button', name='Saving...', exact=True).is_disabled())
                self.assertEqual(page.locator('#action-form').get_attribute('aria-busy'), 'true')
                page.keyboard.press('Escape')
                self.assertTrue(page.get_by_role('dialog').is_visible())
                page.evaluate("document.querySelector('#action-form').dispatchEvent(new Event('submit', {cancelable:true}))")
                self.assertEqual(page.evaluate('window.uxCalls'), 1)
                page.evaluate("window.uxReject(new Error('Family name already exists'))")
                page.wait_for_function("document.activeElement.id === 'form-error'")
                self.assertEqual(field.input_value(), 'KeepMyInput')
                self.assertTrue(page.get_by_role('button', name='Save', exact=True).is_enabled())
                field.fill('CorrectedName')
                page.evaluate("() => { activeAction.custom = async payload => {window.uxSaved = payload.name; return {};}; }")
                page.get_by_role('button', name='Save', exact=True).click()
                page.wait_for_function("!document.querySelector('#dialog').open")
                self.assertEqual(page.evaluate('window.uxSaved'), 'CorrectedName')
                self.assertFalse(errors)
            finally:
                browser.close()
