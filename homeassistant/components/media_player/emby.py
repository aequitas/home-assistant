"""
Support to interface with the Emby API.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.emby/
"""
from datetime import timedelta
import logging

from homeassistant.components.media_player import (
    MEDIA_TYPE_TVSHOW, MEDIA_TYPE_VIDEO, PLATFORM_SCHEMA, SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK, SUPPORT_SEEK, SUPPORT_STOP,
    MediaPlayerDevice)
from homeassistant.const import (
    CONF_API_KEY, CONF_HOST, CONF_PORT, CONF_SSL, DEVICE_DEFAULT_NAME,
    STATE_IDLE, STATE_OFF, STATE_PAUSED, STATE_PLAYING, STATE_UNKNOWN)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import Throttle
import voluptuous as vol

REQUIREMENTS = ['pyemby==0.1']

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=1)

DEFAULT_PORT = 8096

_LOGGER = logging.getLogger(__name__)

SUPPORT_EMBY = SUPPORT_PAUSE | SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | \
    SUPPORT_STOP | SUPPORT_SEEK

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST, default='localhost'): cv.string,
    vol.Optional(CONF_SSL, default=False): cv.boolean,
    vol.Required(CONF_API_KEY): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
})


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the Emby platform."""
    from pyemby.emby import EmbyRemote

    _host = config.get(CONF_HOST)
    _key = config.get(CONF_API_KEY)
    _port = config.get(CONF_PORT)

    if config.get(CONF_SSL):
        _protocol = "https"
    else:
        _protocol = "http"

    _url = '{}://{}:{}'.format(_protocol, _host, _port)

    _LOGGER.debug('Setting up Emby server at: %s', _url)

    embyserver = EmbyRemote(_key, _url)

    emby_clients = {}
    emby_sessions = {}
    track_utc_time_change(hass, lambda now: update_devices(), second=30)

    @Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update_devices():
        """Update the devices objects."""
        devices = embyserver.get_sessions()
        if devices is None:
            _LOGGER.error('Error listing Emby devices.')
            return

        new_emby_clients = []
        for device in devices:
            if device['DeviceId'] == embyserver.unique_id:
                break

            if device['DeviceId'] not in emby_clients:
                _LOGGER.debug('New Emby DeviceID: %s. Adding to Clients.',
                              device['DeviceId'])
                new_client = EmbyClient(embyserver, device, emby_sessions,
                                        update_devices, update_sessions)
                emby_clients[device['DeviceId']] = new_client
                new_emby_clients.append(new_client)
            else:
                emby_clients[device['DeviceId']].set_device(device)

        if new_emby_clients:
            add_devices_callback(new_emby_clients)

    @Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    def update_sessions():
        """Update the sessions objects."""
        sessions = embyserver.get_sessions()
        if sessions is None:
            _LOGGER.error('Error listing Emby sessions')
            return

        emby_sessions.clear()
        for session in sessions:
            emby_sessions[session['DeviceId']] = session

    update_devices()
    update_sessions()


class EmbyClient(MediaPlayerDevice):
    """Representation of a Emby device."""

    # pylint: disable=too-many-arguments, too-many-public-methods,

    def __init__(self, client, device, emby_sessions, update_devices,
                 update_sessions):
        """Initialize the Emby device."""
        self.emby_sessions = emby_sessions
        self.update_devices = update_devices
        self.update_sessions = update_sessions
        self.client = client
        self.set_device(device)

    def set_device(self, device):
        """Set the device property."""
        self.device = device

    @property
    def unique_id(self):
        """Return the id of this emby client."""
        return '{}.{}'.format(
            self.__class__, self.device['DeviceId'])

    @property
    def supports_remote_control(self):
        """Return control ability."""
        return self.device['SupportsRemoteControl']

    @property
    def name(self):
        """Return the name of the device."""
        return 'emby_{}'.format(self.device['DeviceName']) or \
            DEVICE_DEFAULT_NAME

    @property
    def session(self):
        """Return the session, if any."""
        if self.device['DeviceId'] not in self.emby_sessions:
            return None

        return self.emby_sessions[self.device['DeviceId']]

    @property
    def now_playing_item(self):
        """Return the currently playing item, if any."""
        session = self.session
        if session is not None and 'NowPlayingItem' in session:
            return session['NowPlayingItem']

    @property
    def state(self):
        """Return the state of the device."""
        session = self.session
        if session:
            if 'NowPlayingItem' in session:
                if session['PlayState']['IsPaused']:
                    return STATE_PAUSED
                else:
                    return STATE_PLAYING
            else:
                return STATE_IDLE
        # This is nasty. Need to find a way to determine alive
        else:
            return STATE_OFF

        return STATE_UNKNOWN

    def update(self):
        """Get the latest details."""
        self.update_devices(no_throttle=True)
        self.update_sessions(no_throttle=True)

    def play_percent(self):
        """Return current media percent complete."""
        if self.now_playing_item['RunTimeTicks'] and \
                self.session['PlayState']['PositionTicks']:
            try:
                return int(self.session['PlayState']['PositionTicks']) / \
                    int(self.now_playing_item['RunTimeTicks']) * 100
            except KeyError:
                return 0
        else:
            return 0

    @property
    def app_name(self):
        """Return current user as app_name."""
        # Ideally the media_player object would have a user property.
        try:
            return self.device['UserName']
        except KeyError:
            return None

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        if self.now_playing_item is not None:
            try:
                return self.now_playing_item['Id']
            except KeyError:
                return None

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        if self.now_playing_item is None:
            return None
        try:
            media_type = self.now_playing_item['Type']
            if media_type == 'Episode':
                return MEDIA_TYPE_TVSHOW
            elif media_type == 'Movie':
                return MEDIA_TYPE_VIDEO
            return None
        except KeyError:
            return None

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        if self.now_playing_item and self.media_content_type:
            try:
                return int(self.now_playing_item['RunTimeTicks']) / 10000000
            except KeyError:
                return None

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        if self.now_playing_item is not None:
            try:
                return self.client.get_image(
                    self.now_playing_item['ThumbItemId'], 'Thumb',
                    self.play_percent())
            except KeyError:
                try:
                    return self.client.get_image(
                        self.now_playing_item['PrimaryImageItemId'], 'Primary',
                        self.play_percent())
                except KeyError:
                    return None

    @property
    def media_title(self):
        """Title of current playing media."""
        # find a string we can use as a title
        if self.now_playing_item is not None:
            return self.now_playing_item['Name']

    @property
    def media_season(self):
        """Season of curent playing media (TV Show only)."""
        if self.now_playing_item is not None and \
           'ParentIndexNumber' in self.now_playing_item:
            return self.now_playing_item['ParentIndexNumber']

    @property
    def media_series_title(self):
        """The title of the series of current playing media (TV Show only)."""
        if self.now_playing_item is not None and \
           'SeriesName' in self.now_playing_item:
            return self.now_playing_item['SeriesName']

    @property
    def media_episode(self):
        """Episode of current playing media (TV Show only)."""
        if self.now_playing_item is not None and \
           'IndexNumber' in self.now_playing_item:
            return self.now_playing_item['IndexNumber']

    @property
    def supported_media_commands(self):
        """Flag of media commands that are supported."""
        if self.supports_remote_control:
            return SUPPORT_EMBY
        else:
            return None

    def media_play(self):
        """Send play command."""
        if self.supports_remote_control:
            self.client.play(self.session)

    def media_pause(self):
        """Send pause command."""
        if self.supports_remote_control:
            self.client.pause(self.session)

    def media_next_track(self):
        """Send next track command."""
        self.client.next_track(self.session)

    def media_previous_track(self):
        """Send previous track command."""
        self.client.previous_track(self.session)
