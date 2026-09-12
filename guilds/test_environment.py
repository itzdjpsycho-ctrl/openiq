from django.test import SimpleTestCase
from .management.commands.validate_environment import problems


class EnvironmentTests(SimpleTestCase):
    def test_production_requires_oauth_and_rejects_demo_and_password_login(self):
        errors=problems({'SEED_DEMO':'1','ALLOW_LOCAL_LOGIN':'1'},False)
        self.assertTrue(any('DISCORD_CLIENT_SECRET' in error for error in errors))
        self.assertTrue(any('seeding' in error for error in errors))
        self.assertEqual(problems({'DISCORD_CLIENT_ID':'123','DISCORD_CLIENT_SECRET':'private','DISCORD_REDIRECT_URI':'https://guild.example/auth/discord/callback/'},False),[])
        self.assertEqual(problems({},False,'backup'),[])
        self.assertEqual(problems({'ALLOW_LOCAL_LOGIN':'1','SEED_DEMO':'1'},True),[])

    def test_invalid_boolean_delivery_and_sync_are_rejected_without_secrets(self):
        errors=problems({'ENABLE_DISCORD_DELIVERY':'1','DEBUG':'yes','DISCORD_SYNC_GLOBAL':'1','DISCORD_SYNC_GUILD':'123'},True)
        self.assertEqual(len(errors),3)
