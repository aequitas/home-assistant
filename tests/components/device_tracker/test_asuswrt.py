"""The tests for the ASUSWRT device tracker platform."""
from datetime import timedelta
import os
import unittest
from unittest import mock

from homeassistant.bootstrap import setup_component
from homeassistant.components import device_tracker
from homeassistant.components.device_tracker import (
    CONF_CONSIDER_HOME, CONF_TRACK_NEW)
from homeassistant.components.device_tracker.asuswrt import (
    CONF_MODE, CONF_PROTOCOL, CONF_PUB_KEY, DOMAIN, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_HOST, CONF_PASSWORD, CONF_PLATFORM, CONF_USERNAME)
from tests.common import (
    assert_setup_component, get_test_config_dir, get_test_home_assistant)
import voluptuous as vol

FAKEFILE = None


def setup_module():
    """Setup the test module."""
    global FAKEFILE
    FAKEFILE = get_test_config_dir('fake_file')
    with open(FAKEFILE, 'w') as out:
        out.write(' ')


def teardown_module():
    """Tear down the module."""
    os.remove(FAKEFILE)


class TestComponentsDeviceTrackerASUSWRT(unittest.TestCase):
    """Tests for the ASUSWRT device tracker platform."""

    hass = None

    def setup_method(self, _):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.components = ['zone']

    def teardown_method(self, _):
        """Stop everything that was started."""
        try:
            os.remove(self.hass.config.path(device_tracker.YAML_DEVICES))
        except FileNotFoundError:
            pass

    def test_password_or_pub_key_required(self): \
            # pylint: disable=invalid-name
        """Test creating an AsusWRT scanner without a pass or pubkey."""
        with assert_setup_component(0):
            assert setup_component(
                self.hass, DOMAIN, {DOMAIN: {
                    CONF_PLATFORM: 'asuswrt',
                    CONF_HOST: 'fake_host',
                    CONF_USERNAME: 'fake_user'
                }})

    @mock.patch(
        'homeassistant.components.device_tracker.asuswrt.AsusWrtDeviceScanner',
        return_value=mock.MagicMock())
    def test_get_scanner_with_password_no_pubkey(self, asuswrt_mock):  \
            # pylint: disable=invalid-name
        """Test creating an AsusWRT scanner with a password and no pubkey."""
        conf_dict = {
            DOMAIN: {
                CONF_PLATFORM: 'asuswrt',
                CONF_HOST: 'fake_host',
                CONF_USERNAME: 'fake_user',
                CONF_PASSWORD: 'fake_pass',
                CONF_TRACK_NEW: True,
                CONF_CONSIDER_HOME: timedelta(seconds=180)
            }
        }

        with assert_setup_component(1):
            assert setup_component(self.hass, DOMAIN, conf_dict)

        conf_dict[DOMAIN][CONF_MODE] = 'router'
        conf_dict[DOMAIN][CONF_PROTOCOL] = 'ssh'
        self.assertEqual(asuswrt_mock.call_count, 1)
        self.assertEqual(asuswrt_mock.call_args, mock.call(conf_dict[DOMAIN]))

    @mock.patch(
        'homeassistant.components.device_tracker.asuswrt.AsusWrtDeviceScanner',
        return_value=mock.MagicMock())
    def test_get_scanner_with_pubkey_no_password(self, asuswrt_mock):  \
            # pylint: disable=invalid-name
        """Test creating an AsusWRT scanner with a pubkey and no password."""
        conf_dict = {
            device_tracker.DOMAIN: {
                CONF_PLATFORM: 'asuswrt',
                CONF_HOST: 'fake_host',
                CONF_USERNAME: 'fake_user',
                CONF_PUB_KEY: FAKEFILE,
                CONF_TRACK_NEW: True,
                CONF_CONSIDER_HOME: timedelta(seconds=180)
            }
        }

        with assert_setup_component(1):
            assert setup_component(self.hass, DOMAIN, conf_dict)

        conf_dict[DOMAIN][CONF_MODE] = 'router'
        conf_dict[DOMAIN][CONF_PROTOCOL] = 'ssh'
        self.assertEqual(asuswrt_mock.call_count, 1)
        self.assertEqual(asuswrt_mock.call_args, mock.call(conf_dict[DOMAIN]))

    def test_ssh_login_with_pub_key(self):
        """Test that login is done with pub_key when configured to."""
        ssh = mock.MagicMock()
        ssh_mock = mock.patch('pexpect.pxssh.pxssh', return_value=ssh)
        ssh_mock.start()
        self.addCleanup(ssh_mock.stop)
        conf_dict = PLATFORM_SCHEMA({
            CONF_PLATFORM: 'asuswrt',
            CONF_HOST: 'fake_host',
            CONF_USERNAME: 'fake_user',
            CONF_PUB_KEY: FAKEFILE
        })
        update_mock = mock.patch(
            'homeassistant.components.device_tracker.asuswrt.'
            'AsusWrtDeviceScanner.get_asuswrt_data')
        update_mock.start()
        self.addCleanup(update_mock.stop)
        asuswrt = device_tracker.asuswrt.AsusWrtDeviceScanner(conf_dict)
        asuswrt.ssh_connection()
        self.assertEqual(ssh.login.call_count, 1)
        self.assertEqual(
            ssh.login.call_args,
            mock.call('fake_host', 'fake_user', ssh_key=FAKEFILE)
        )

    def test_ssh_login_with_password(self):
        """Test that login is done with password when configured to."""
        ssh = mock.MagicMock()
        ssh_mock = mock.patch('pexpect.pxssh.pxssh', return_value=ssh)
        ssh_mock.start()
        self.addCleanup(ssh_mock.stop)
        conf_dict = PLATFORM_SCHEMA({
            CONF_PLATFORM: 'asuswrt',
            CONF_HOST: 'fake_host',
            CONF_USERNAME: 'fake_user',
            CONF_PASSWORD: 'fake_pass'
        })
        update_mock = mock.patch(
            'homeassistant.components.device_tracker.asuswrt.'
            'AsusWrtDeviceScanner.get_asuswrt_data')
        update_mock.start()
        self.addCleanup(update_mock.stop)
        asuswrt = device_tracker.asuswrt.AsusWrtDeviceScanner(conf_dict)
        asuswrt.ssh_connection()
        self.assertEqual(ssh.login.call_count, 1)
        self.assertEqual(
            ssh.login.call_args,
            mock.call('fake_host', 'fake_user', password='fake_pass')
        )

    def test_ssh_login_without_password_or_pubkey(self):  \
            # pylint: disable=invalid-name
        """Test that login is not called without password or pub_key."""
        ssh = mock.MagicMock()
        ssh_mock = mock.patch('pexpect.pxssh.pxssh', return_value=ssh)
        ssh_mock.start()
        self.addCleanup(ssh_mock.stop)

        conf_dict = {
            CONF_PLATFORM: 'asuswrt',
            CONF_HOST: 'fake_host',
            CONF_USERNAME: 'fake_user',
        }

        with self.assertRaises(vol.Invalid):
            conf_dict = PLATFORM_SCHEMA(conf_dict)

        update_mock = mock.patch(
            'homeassistant.components.device_tracker.asuswrt.'
            'AsusWrtDeviceScanner.get_asuswrt_data')
        update_mock.start()
        self.addCleanup(update_mock.stop)

        with assert_setup_component(0):
            assert setup_component(self.hass, DOMAIN,
                                   {DOMAIN: conf_dict})
        ssh.login.assert_not_called()
