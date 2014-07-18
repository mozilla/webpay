from django.core.urlresolvers import reverse

import json
from mock import ANY, Mock, patch
from nose.tools import eq_
from pyquery import PyQuery as pq

from lib.solitude import constants
from lib.solitude.api import client
from lib.solitude.errors import ERROR_STRINGS
from webpay.auth.tests import SessionTestCase
from webpay.pay import get_wait_url


class PinViewTestCase(SessionTestCase):
    url_name = ''

    def setUp(self):
        super(PinViewTestCase, self).setUp()
        self.url = reverse(self.url_name)
        self.uuid = 'fake:buyer_uuid'
        self.email = 'fake@user.com'
        self.verify(self.uuid, self.email)


class CreatePinViewTest(PinViewTestCase):
    url_name = 'pin.create'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    def test_buyer_does_exist_with_no_pin(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert change_pin.called
        assert res['Location'].endswith(reverse('pin.confirm'))

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin')
    @patch.object(client, 'get_buyer', lambda x: {
        'uuid': 'some:uuid', 'etag': 'etag'})
    def test_buyer_does_exist_with_no_pin_and_etag(self, change_pin,
                                                   create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert change_pin.called
        change_pin.assert_called_with(self.uuid, pin='1234', etag='etag')
        assert res['Location'].endswith(reverse('pin.confirm'))

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid',
                                                  'pin': 'fake'})
    def test_buyer_does_exist_with_pin(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert not change_pin.called
        eq_(res.status_code, 200)
        doc = pq(res.content)
        form_tracking_data = json.loads(doc('#pin').attr('data-tracking'))
        eq_(form_tracking_data['pin_error_codes'], ['PIN_ALREADY_CREATED'])

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    @patch.object(client, 'change_pin',
                  lambda *args, **kwargs: {
                      'errors': {
                          'pin': [ERROR_STRINGS['PIN_4_NUMBERS_LONG']]}})
    def test_buyer_does_exist_with_short_pin(self, create_buyer):
        res = self.client.post(self.url, data={'pin': '123'})
        assert not create_buyer.called
        form = res.context['form']
        eq_(form.errors.get('pin'), [ERROR_STRINGS['PIN_4_NUMBERS_LONG']])

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    @patch.object(client, 'change_pin',
                  lambda *args, **kwargs: {
                      'errors': {
                          'pin': [ERROR_STRINGS['PIN_ONLY_NUMBERS']]}})
    def test_buyer_does_exist_with_alpha_pin(self, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        form = res.context['form']
        eq_(form.errors.get('pin'), [ERROR_STRINGS['PIN_ONLY_NUMBERS']])


class VerifyPinViewTest(PinViewTestCase):
    url_name = 'pin.verify'

    def setUp(self):
        super(VerifyPinViewTest, self).setUp()
        self.session['uuid_has_pin'] = True
        self.session['uuid_has_confirmed_pin'] = True
        self.save_session()

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': False,
                                                      'valid': True})
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert res['Location'].endswith(get_wait_url(Mock(session={})))

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': False,
                                                      'valid': False})
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        eq_(res.status_code, 200)
        doc = pq(res.content)
        form_tracking_data = json.loads(doc('#pin').attr('data-tracking'))
        eq_(form_tracking_data['pin_error_codes'], ['WRONG_PIN'])

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': True,
                                                      'valid': False})
    def test_locked_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        eq_(res.status_code, 302)
        assert res.get('Location', '').endswith(reverse('pin.is_locked'))

    @patch.object(client, 'verify_pin')
    def test_uuid_used(self, verify_pin):
        verify_pin.return_value = {'locked': False, 'valid': True}
        self.client.post(self.url, data={'pin': '1234'})
        eq_(verify_pin.call_args[0][0], self.uuid)

    def test_needs_verified_pin(self):
        self.session['uuid_has_confirmed_pin'] = False
        self.save_session()
        res = self.client.post(self.url)
        eq_(res.status_code, 302)
        assert res.get('Location', '').endswith(reverse('pin.confirm'))

    def test_redirects_to_reset_flow(self):
        self.session['was_reverified'] = True
        self.session['uuid_needs_pin_reset'] = True
        self.save_session()
        res = self.client.post(self.url)
        eq_(res.status_code, 302)
        assert res.get('Location', '').endswith(reverse('pin.reset_new_pin'))

    def test_redirects_to_locked_view(self):
        self.session['uuid_pin_is_locked'] = True
        self.save_session()
        res = self.client.get(self.url)
        assert res['Location'].endswith(reverse('pin.is_locked'))


class ConfirmPinViewTest(PinViewTestCase):
    url_name = 'pin.confirm'

    def setUp(self):
        super(ConfirmPinViewTest, self).setUp()
        self.session['uuid_has_confirmed_pin'] = False
        self.session['uuid_has_pin'] = True
        self.save_session()

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch.object(client, 'confirm_pin', lambda x, y: True)
    @patch('webpay.pin.views.set_user_has_confirmed_pin', auto_spec=True)
    def test_good_pin(self, set_user_has_confirmed_pin):
        res = self.client.post(self.url, data={'pin': '1234'})
        set_user_has_confirmed_pin.assert_called_with(ANY, True)
        assert res['Location'].endswith(get_wait_url(Mock(session={})))

    @patch.object(client, 'confirm_pin', lambda x, y: False)
    @patch('webpay.pin.views.set_user_has_confirmed_pin', auto_spec=True)
    def test_bad_pin(self, set_user_has_confirmed_pin):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not set_user_has_confirmed_pin.called
        eq_(res.status_code, 200)
        doc = pq(res.content)
        form_tracking_data = json.loads(doc('#pin').attr('data-tracking'))
        eq_(form_tracking_data['pin_error_codes'], ['PINS_DONT_MATCH'])

    @patch.object(client, 'confirm_pin')
    def test_uuid_used(self, confirm_pin):
        confirm_pin.return_value = True
        self.client.post(self.url, data={'pin': '1234'})
        eq_(confirm_pin.call_args[0][0], self.uuid)

    def test_needs_pin(self):
        self.session['uuid_has_pin'] = False
        self.save_session()
        res = self.client.post(self.url)
        eq_(res.status_code, 302)
        assert res.get('Location', '').endswith(reverse('pin.create'))


class IsLockedPinViewTest(PinViewTestCase):
    url_name = 'pin.is_locked'

    def setUp(self):
        super(IsLockedPinViewTest, self).setUp()
        self.session['uuid_pin_is_locked'] = True
        self.session['uuid_has_confirmed_pin'] = True
        self.session['uuid_has_pin'] = True
        self.save_session()

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    def test_get(self):
        res = self.client.get(self.url)
        eq_(res.status_code, 200)

    def test_is_not_locked(self):
        self.session['uuid_pin_is_locked'] = False
        self.save_session()
        res = self.client.get(self.url)
        assert res['Location'].endswith(reverse('pin.verify'))


class WasLockedPinViewTest(PinViewTestCase):
    url_name = 'pin.was_locked'

    def setUp(self):
        super(WasLockedPinViewTest, self).setUp()
        self.session['uuid_pin_was_locked'] = True
        self.session['uuid_has_confirmed_pin'] = True
        self.session['uuid_has_pin'] = True
        self.save_session()

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch.object(client, 'unset_was_locked', lambda uuid: {})
    def test_get(self):
        res = self.client.get(self.url)
        eq_(res.status_code, 200)

    def test_was_not_locked(self):
        self.session['uuid_pin_was_locked'] = False
        self.save_session()
        res = self.client.get(self.url)
        assert res['Location'].endswith(reverse('pin.verify'))


class ResetStartViewTest(PinViewTestCase):
    url_name = 'pin.reset_start'

    def setUp(self):
        super(ResetStartViewTest, self).setUp()
        self.session['uuid_has_confirmed_pin'] = True
        self.session['uuid_needs_pin_reset'] = True
        self.save_session()

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.set_needs_pin_reset', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_view(self, set_needs_pin_reset):
        self.session['uuid_needs_pin_reset'] = False
        self.save_session()
        res = self.client.get(self.url)
        form = res.context['form']
        eq_(res.status_code, 200)
        eq_(form.reset_flow, True)
        assert set_needs_pin_reset.called

    def test_redirects_to_locked_view(self):
        self.session['uuid_pin_is_locked'] = True
        self.save_session()
        res = self.client.get(self.url)
        assert res['Location'].endswith(reverse('pin.is_locked'))

    @patch('lib.solitude.api.client.set_needs_pin_reset', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_refresh_view(self, set_needs_pin_reset):
        res = self.client.get(self.url)
        eq_(res.status_code, 200)
        form = res.context['form']
        eq_(form.reset_flow, True)
        assert set_needs_pin_reset.called


class ResetPinTest(PinViewTestCase):

    def setUp(self):
        super(ResetPinTest, self).setUp()
        # Simulate a previous Persona user/pass reverification.
        self.session['was_reverified'] = True
        self.save_session()


class ResetNewPinViewTest(ResetPinTest):
    url_name = 'pin.reset_new_pin'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.set_new_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_valid_form(self, set_new_pin):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert set_new_pin.called
        assert res['Location'].endswith(reverse('pin.reset_confirm'))

    @patch('lib.solitude.api.client.set_new_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_attempt_before_reverify(self, set_new_pin):
        self.session['uuid_needs_pin_reset'] = True
        self.session['was_reverified'] = False
        self.save_session()
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not set_new_pin.called
        assert res['Location'].endswith(reverse('pin.reset_start'))

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    @patch.object(client, 'set_new_pin',
                  lambda x, y: {'errors':
                                {'pin':
                                 [ERROR_STRINGS['PIN_4_NUMBERS_LONG']]}})
    def test_short_pin(self):
        res = self.client.post(self.url, data={'pin': '123'})
        form = res.context['form']
        eq_(form.errors.get('pin'), [ERROR_STRINGS['PIN_4_NUMBERS_LONG']])

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    @patch.object(client, 'set_new_pin',
                  lambda x, y: {'errors':
                                {'pin': [ERROR_STRINGS['PIN_ONLY_NUMBERS']]}})
    def test_alpha_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        form = res.context['form']
        eq_(form.errors.get('pin'), [ERROR_STRINGS['PIN_ONLY_NUMBERS']])

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    @patch.object(client, 'set_new_pin',
                  lambda x, y: {'errors':
                                {'new_pin':
                                 [ERROR_STRINGS['PIN_4_NUMBERS_LONG']]}})
    def test_short_new_pin(self):
        res = self.client.post(self.url, data={'pin': '123'})
        form = res.context['form']
        eq_(form.errors.get('pin'), [ERROR_STRINGS['PIN_4_NUMBERS_LONG']])

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    @patch.object(client, 'set_new_pin',
                  lambda x, y: {'errors': {
                      'new_pin': [ERROR_STRINGS['PIN_ONLY_NUMBERS']]}})
    def test_alpha_new_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        form = res.context['form']
        eq_(form.errors.get('pin'), [ERROR_STRINGS['PIN_ONLY_NUMBERS']])

    def test_redirects_to_locked_view(self):
        self.session['uuid_pin_is_locked'] = True
        self.save_session()
        res = self.client.get(self.url)
        assert res['Location'].endswith(reverse('pin.is_locked'))


class ResetConfirmPinViewTest(ResetPinTest):
    url_name = 'pin.reset_confirm'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    def add_fake_trans_id_to_session(self):
        sess = self.client.session
        sess['trans_id'] = 'some:uuid'
        self.save_session(sess)

    @patch.object(client, 'reset_confirm_pin', lambda x, y: True)
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert res['Location'].endswith(get_wait_url(Mock(session={})))
        # Make sure the reverification flag was cleared out.
        eq_(res.client.session['was_reverified'], False)

    @patch.object(client, 'reset_confirm_pin', lambda x, y: True)
    def test_attempt_before_reverify(self):
        self.session['uuid_needs_pin_reset'] = True
        self.session['was_reverified'] = False
        self.save_session()
        res = self.client.post(self.url, data={'pin': '1234'})
        assert res['Location'].endswith(reverse('pin.reset_start'))

    @patch.object(client, 'reset_confirm_pin', lambda x, y: True)
    @patch('lib.solitude.api.client.get_transaction', auto_spec=True)
    def test_messages_in_pin_reset(self, get_transaction):
        get_transaction.return_value = {'status': 'foo'}
        self.add_fake_trans_id_to_session()
        res = self.client.post(self.url, data={'pin': '1234'}, follow=True)
        eq_([u'Pin reset'], [msg.message for msg in res.context['messages']])

    @patch.object(client, 'reset_confirm_pin', lambda x, y: True)
    @patch('lib.solitude.api.client.get_transaction', auto_spec=True)
    def test_messages_cleared_in_pin_reset(self, get_transaction):
        get_transaction.return_value = {
            'status': constants.STATUS_PENDING, 'uid_pay': 1,
            'pay_url': 'https://bango/pay'
        }
        self.add_fake_trans_id_to_session()
        res = self.client.post(self.url, data={'pin': '1234'}, follow=True)
        eq_([], [msg.message for msg in res.context['messages']])

    @patch.object(client, 'reset_confirm_pin', lambda x, y: False)
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        eq_(res.status_code, 200)
        doc = pq(res.content)
        form_tracking_data = json.loads(doc('#pin').attr('data-tracking'))
        eq_(form_tracking_data['pin_error_codes'], ['PINS_DONT_MATCH'])

    @patch.object(client, 'reset_confirm_pin')
    def test_uuid_used(self, confirm_pin):
        confirm_pin.return_value = True
        self.client.post(self.url, data={'pin': '1234'})
        eq_(confirm_pin.call_args[0][0], self.uuid)


class ResetCancelViewTest(PinViewTestCase):
    url_name = 'pin.reset_cancel'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.set_needs_pin_reset', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_view(self, set_needs_pin_reset):
        res = self.client.get(self.url)
        assert set_needs_pin_reset.called
        assert res['Location'].endswith(reverse('pin.verify'))
