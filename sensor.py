"""
Support for EnergyEasy.

Get data from 'Energy Easy' page/s:
https://energyeasy.ue.com.au/electricityView/index

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.EnergyEasy/
"""
import logging
from datetime import timedelta
import json

import re
from bs4 import BeautifulSoup
import requests
import logging

import http.client as http_client

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_USERNAME, CONF_PASSWORD,
    CONF_NAME, CONF_MONITORED_VARIABLES)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['beautifulsoup4==4.6.0']

http_client.HTTPConnection.debuglevel = 1

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

REQUESTS_TIMEOUT = 15

KILOWATT_HOUR = 'kWh'  # type: str
PRICE = 'AUD'          # type: str
DAYS = 'days'          # type: str
PERCENT = '%'          # type: str

DEFAULT_NAME = 'EnergyEasy'

REQUESTS_TIMEOUT = 15
MIN_TIME_BETWEEN_UPDATES = timedelta(hours=24)
SCAN_INTERVAL = timedelta(hours=24)

SENSOR_TYPES = {
    'yesterday_user_type': ['Yesterday user type', 'type', 'mdi:home-account'],
    'yesterday_usage': ['Yesterday usage', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_consumption': ['Yesterday consumption', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_consumption_peak': ['Yesterday consumption peak', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_consumption_offpeak': ['Yesterday consumption offpeak', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_consumption_shoulder': ['Yesterday consumption shoulder', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_generation': ['Yesterday generation', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_cost_total': ['Yesterday cost total', PRICE, 'mdi:currency-usd'],
    'yesterday_cost_consumption': ['Yesterday cost consumption', PRICE, 'mdi:currency-usd'],
    'yesterday_cost_generation': ['Yesterday cost generation', PRICE, 'mdi:currency-usd'],
    'yesterday_cost_difference': ['Yesterday cost difference', PRICE, 'mdi:currency-usd'],
    'yesterday_percentage_difference': ['Yesterday percentage difference', PERCENT, 'mdi:percent'],
    'yesterday_difference_message': ['Yesterday difference message', 'text', 'mdi:clipboard-text'],
    'yesterday_consumption_difference': ['Yesterday consumption difference', KILOWATT_HOUR, 'mdi:flash'],
    'yesterday_consumption_change': ['Yesterday consumption change', KILOWATT_HOUR, 'mdi:swap-vertical'],
    'yesterday_suburb_average': ['Yesterday suburb average', KILOWATT_HOUR, 'mdi:flash'],
    'previous_day_usage': ['Previous day usage', KILOWATT_HOUR, 'mdi:flash'],
    'previous_day_consumption': ['Previous day consumption', KILOWATT_HOUR, 'mdi:flash'],
    'previous_day_generation': ['Previous day generation', KILOWATT_HOUR, 'mdi:flash'],
    'supply_charge': ['Supply charge', PRICE, 'mdi:currency-usd'],
    'weekday_peak_cost': ['Weekday peak cost', PRICE, 'mdi:currency-usd'],
    'weekday_offpeak_cost': ['Weekday offpeak cost', PRICE, 'mdi:currency-usd'],
    'weekday_shoulder_cost': ['Weekday shoulder cost', PRICE, 'mdi:currency-usd'],
    'weekend_offpeak_cost': ['Weekend offpeak cost', PRICE, 'mdi:currency-usd'],
    'single_rate_cost': ['Single rate cost', PRICE, 'mdi:currency-usd'],
    'generation_cost': ['Generation cost', PRICE, 'mdi:currency-usd'],
    'this_week_user_type': ['This week user type', 'type', 'mdi:home-account'],
    'this_week_usage': ['This week usage', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_consumption': ['This week consumption', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_consumption_peak': ['This week consumption peak', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_consumption_offpeak': ['This week consumption offpeak', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_consumption_shoulder': ['This week consumption shoulder', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_generation': ['This week generation', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_cost_total': ['This week cost total', PRICE, 'mdi:currency-usd'],
    'this_week_cost_consumption': ['This week cost consumption', PRICE, 'mdi:currency-usd'],
    'this_week_cost_generation': ['This week cost generation', PRICE, 'mdi:currency-usd'],
    'this_week_cost_difference': ['This week cost difference', PRICE, 'mdi:currency-usd'],
    'this_week_percentage_difference': ['This week percentage difference', PERCENT, 'mdi:percent'],
    'this_week_difference_message': ['This week difference message', 'text', 'mdi:clipboard-text'],
    'this_week_consumption_difference': ['This week consumption difference', KILOWATT_HOUR, 'mdi:flash'],
    'this_week_consumption_change': ['This week consumption change', KILOWATT_HOUR, 'mdi:swap-vertical'],
    'this_week_suburb_average': ['This week suburb average', KILOWATT_HOUR, 'mdi:flash'],
    'last_week_usage': ['Last week usage', KILOWATT_HOUR, 'mdi:flash'],
    'last_week_consumption': ['Last week consumption', KILOWATT_HOUR, 'mdi:flash'],
    'last_week_generation': ['Last week generation', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_user_type': ['This month user type', 'type', 'mdi:home-account'],
    'this_month_usage': ['This month usage', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_consumption': ['This month consumption', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_consumption_peak': ['This month consumption peak', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_consumption_offpeak': ['This month consumption offpeak', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_consumption_shoulder': ['This month consumption shoulder', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_generation': ['This month generation', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_cost_total': ['This month cost total', PRICE, 'mdi:currency-usd'],
    'this_month_cost_consumption': ['This month cost consumption', PRICE, 'mdi:currency-usd'],
    'this_month_cost_generation': ['This month cost generation', PRICE, 'mdi:currency-usd'],
    'this_month_cost_difference': ['This month cost difference', PRICE, 'mdi:currency-usd'],
    'this_month_percentage_difference': ['This month percentage difference', PERCENT, 'mdi:percent'],
    'this_month_difference_message': ['This month difference message', 'text', 'mdi:clipboard-text'],
    'this_month_consumption_difference': ['This month consumption difference', KILOWATT_HOUR, 'mdi:flash'],
    'this_month_consumption_change': ['This month consumption change', KILOWATT_HOUR, 'mdi:swap-vertical'],
    'this_month_suburb_average': ['This month suburb average', KILOWATT_HOUR, 'mdi:flash'],
    'last_month_usage': ['Last month usage', KILOWATT_HOUR, 'mdi:flash'],
    'last_month_consumption': ['Last month consumption', KILOWATT_HOUR, 'mdi:flash'],
    'last_month_generation': ['Last month generation', KILOWATT_HOUR, 'mdi:flash'],
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_MONITORED_VARIABLES):
        vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

HOST = 'https://energyeasy.ue.com.au'
HOME_URL = '{}/login/index'.format(HOST)
PERIOD_URL = ('{}/electricityView/period'.format(HOST))


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Energy Easy sensor."""
    # Create a data fetcher to support all of the configured sensors. Then make
    # the first call to init the data.

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    try:
        _LOGGER.info(username)
        _LOGGER.info(password)
        energyeasy_data = EnergyEasyData(username, password)
        energyeasy_data.get_data()
        
    except requests.exceptions.HTTPError as error:
        _LOGGER.error("Failed login: %s", error)
        return False

    name = config.get(CONF_NAME)

    sensors = []
    for variable in config[CONF_MONITORED_VARIABLES]:
        sensors.append(EnergyEasySensor(energyeasy_data, variable, name))

    add_devices(sensors)


class EnergyEasySensor(Entity):
    """Implementation of a Energy Easy sensor."""

    def __init__(self, energyeasy_data, sensor_type, name):
        """Initialize the sensor."""
        self.client_name = name
        self.type = sensor_type
        self._name = SENSOR_TYPES[sensor_type][0]
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        self._icon = SENSOR_TYPES[sensor_type][2]
        self.energyeasy_data = energyeasy_data
        self._state = None

        _LOGGER.info('init data: %s', energyeasy_data.data)

        if self.type in self.energyeasy_data.data is not None:
            if type(self.energyeasy_data.data[self.type]) == type(''):
                self._state = self.energyeasy_data.data[self.type]
            else:
                self._state = round(self.energyeasy_data.data[self.type], 2)
                

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self.client_name, self._name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    def update(self):
        """Get the latest data from Energy Easy and update the state."""
        self.energyeasy_data.update()

        if self.type in self.energyeasy_data.data is not None:
            if type(self.energyeasy_data.data[self.type]) == type(''):
                self._state = self.energyeasy_data.data[self.type]
            else:
                self._state = round(self.energyeasy_data.data[self.type], 2)


class EnergyEasyData(object):
    """Get data from EnergyEasy."""

    def __init__(self, username, password):
        """Initialize the data object."""
        self.client = EnergyEasyClient(
            username, password, REQUESTS_TIMEOUT)
        self.data = {}

    def _fetch_data(self):
        """Fetch latest data from Energy Easy."""
        try:
            self.client.fetch_data()
        except EnergyEasyError as exp:
            _LOGGER.error("Error on receiving last Energy Easy data: %s", exp)
            return

    def get_data(self):
        """Return the contract list."""
        # Fetch data
        self._fetch_data()
        self.data = self.client.get_data()
        return self.data

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Return the latest collected data from Energy Easy."""
        self._fetch_data()
        self.data = self.client.get_data()


class EnergyEasyError(Exception):
    pass

class EnergyEasyClient(object):

    def __init__(self, username, password, timeout=REQUESTS_TIMEOUT):
        """Initialize the client object."""
        self.username = username
        self.password = password
        self._data = {}
        self._timeout = timeout
        self._session = None


    def _get_login_page(self):
        """Go to the login page."""
        try:
            raw_res = self._session.get(HOME_URL, timeout=REQUESTS_TIMEOUT)

        except OSError:
            raise EnergyEasyError("Can not connect to login page")

        # Get login url
        soup = BeautifulSoup(raw_res.content, 'html.parser')

        form_node = soup.find('form', {'id': 'loginForm'})
        if form_node is None:
            raise EnergyEasyError("No login form found")

        login_url = form_node.attrs.get('action')
        if login_url is None:
            raise EnergyEasyError("Cannot find login url")

        return login_url


    def _post_login_page(self, login_url):
        """Login to Jemena Electricity Outlook website."""
        form_data = {"login_email": self.username,
                "login_password": self.password,
                "submit": "Sign In"}
        try:
            raw_res = self._session.post('{}/login_security_check'.format(HOST),
                                    data = form_data,
                                    timeout = REQUESTS_TIMEOUT)

        except OSError as e:
            raise EnergyEasyError("Cannot submit login form {0}".format(e.errno))
        
        if raw_res.status_code != 200:
            raise EnergyEasyError("Login error: Bad HTTP status code. {}".format(raw_res.status_code))

        return True

    
    def _get_tariffs(self):
        """Get tariff data. This data must be setup by the user first and is not automatically available."""

        try:
            url = '{}/electricityView/index'.format(HOST)
            raw_res = self._session.get(url, timeout=REQUESTS_TIMEOUT)

        except OSError:
            raise EnergyEasyError("Can not connect to login page")

        # Get login url
        soup = BeautifulSoup(raw_res.content, 'html.parser')
        tariff_script = soup.find('script', text=re.compile('var tariff = '))

        if tariff_script is not None:
            
            json_text = re.search(r'^\s*var tariff =\s*({.*?})\s*;\s*$', tariff_script.string, flags=re.DOTALL | re.MULTILINE).group(1)
            data = json.loads(json_text)
        
            tariff_data = {
                "supply_charge": self._strip_currency(data["supplyCharge"]),
                "weekday_peak_cost": self._strip_currency(data["weekdayPeakCost"]),
                "weekday_offpeak_cost": self._strip_currency(data["weekdayOffpeakCost"]),
                "weekday_shoulder_cost": self._strip_currency(data["weekdayShoulderCost"]),
                "weekend_offpeak_cost": self._strip_currency(data["weekendOffpeakCost"]),            
                "single_rate_cost": self._strip_currency(data["singleRateCost"]),
                "generation_cost": self._strip_currency(data["generationCost"]),
                }

        return tariff_data
    
    
    def _get_daily_data(self, days_ago):
        """Get daily data."""

        try:
            #'{}/electricityView/period/day/1'.format(HOST)
            url = '{}/{}/{}'.format(PERIOD_URL, 'day', days_ago)
            raw_res = self._session.get(url, timeout = REQUESTS_TIMEOUT)
        except OSError as e:
            _LOGGER.debug("exception data {}".format(e.errstring))
            raise EnergyEasyError("Cannot get daily data")
        try:
            json_output = raw_res.json()
        except (OSError, json.decoder.JSONDecodeError):
            raise EnergyEasyError("Could not get daily data: {}".format(raw_res))

        if not json_output.get('selectedPeriod'):
            raise EnergyEasyError("Could not get daily data for selectedPeriod")

        _LOGGER.debug("Energy Easy daily data: %s", json_output)

        daily_data = self._extract_period_data(json_output , 'yesterday', 'previous_day')

        return daily_data      



    def _get_weekly_data(self, weeks_ago):
        """Get weekly data."""

        try:
            #PERIOD_URL
            url = '{}/{}/{}'.format(PERIOD_URL, 'week', weeks_ago)
            raw_res = self._session.get(url, timeout = REQUESTS_TIMEOUT)

        except OSError as e:
            _LOGGER.debug("exception data {}".format(e.errstring))
            raise EnergyEasyError("Cannot get daily data")
        try:
            json_output = raw_res.json()

        except (OSError, json.decoder.JSONDecodeError):
            raise EnergyEasyError("Could not get daily data: {}".format(raw_res))

        if not json_output.get('selectedPeriod'):
            raise EnergyEasyError("Could not get daily data for selectedPeriod")

        _LOGGER.debug("Energy Easy weekly data: %s", json_output)
        
        weekly_data = self._extract_period_data(json_output, 'this_week', 'last_week')

        return weekly_data


    def _get_monthly_data(self, months_ago):
        """Get weekly data."""

        try:
            #PERIOD_URL
            url = '{}/{}/{}'.format(PERIOD_URL, 'month', months_ago)
            raw_res = self._session.get(url, timeout = REQUESTS_TIMEOUT)

        except OSError as e:
            _LOGGER.debug("exception data {}".format(e.errstring))
            raise EnergyEasyError("Cannot get daily data")
        try:
            json_output = raw_res.json()

        except (OSError, json.decoder.JSONDecodeError):
            raise EnergyEasyError("Could not get daily data: {}".format(raw_res))

        if not json_output.get('selectedPeriod'):
            raise EnergyEasyError("Could not get daily data for selectedPeriod")

        _LOGGER.debug("Energy Easy monthly data: %s", json_output)
        
        monthly_data = self._extract_period_data(json_output, 'this_month', 'last_month')

        return monthly_data


    def _extract_period_data(self, json_data, current, previous):

        costDifference = json_data.get('costDifference')
        costDifferenceMessage = json_data.get('costDifferenceMessage')
        kwhPercentageDifference = json_data.get('kwhPercentageDifference')

        consumptionDifference = json_data.get('consumptionDifferenceMessage')
        
        selectedPeriod = json_data.get('selectedPeriod')        	
        
        netConsumption = selectedPeriod['netConsumption']
        averageNetConsumptionPerSubPeriod = selectedPeriod['averageNetConsumptionPerSubPeriod']
        peakConsumption = self._sum_period_array(selectedPeriod['consumptionData']['peak'], 3)
        offPeakConsumption = self._sum_period_array(selectedPeriod['consumptionData']['offpeak'], 3)
        shoulderConsumption = self._sum_period_array(selectedPeriod['consumptionData']['shoulder'], 3)
        generation = self._sum_period_array(selectedPeriod['consumptionData']['generation'], 3)
        suburbAverage = self._sum_period_array(selectedPeriod['consumptionData']['suburbAverage'], 3)

        costDataPeak = self._sum_period_array(selectedPeriod['costData']['peak'], 2)
        costDataOffPeak = self._sum_period_array(selectedPeriod['costData']['offpeak'], 2)
        costDataShoulder = self._sum_period_array(selectedPeriod['costData']['shoulder'], 2)
        costDataGeneration = self._sum_period_array(selectedPeriod['costData']['generation'], 2)

        previousPeriod = json_data.get('comparisonPeriod')

        previousPeriodNetConsumption = previousPeriod['netConsumption']
        previousPeriodPeakConsumption = self._sum_period_array(previousPeriod['consumptionData']['peak'], 3)
        previousPeriodOffPeakConsumption = self._sum_period_array(previousPeriod['consumptionData']['offpeak'], 3)
        previousPeriodShoulderConsumption = self._sum_period_array(previousPeriod['consumptionData']['shoulder'], 3)
        previousPeriodGeneration = self._sum_period_array(previousPeriod['consumptionData']['generation'], 3)
        previousPeriodSuburbAverage = self._sum_period_array(previousPeriod['consumptionData']['suburbAverage'], 3)

        period_data = {
            current + "_user_type": "consumer" if netConsumption > 0 else "generator",
            current + "_usage": netConsumption,
            current + "_average_net_usage_per_sub_period": averageNetConsumptionPerSubPeriod,
            current + "_consumption": round(peakConsumption + offPeakConsumption + shoulderConsumption, 3),
            current + "_consumption_peak": peakConsumption,
            current + "_consumption_offpeak": offPeakConsumption,
            current + "_consumption_shoulder": shoulderConsumption,
            current + "_generation": generation,
            current + "_cost_total": round(costDataPeak + costDataOffPeak + costDataShoulder + costDataGeneration, 2),
            current + "_cost_consumption": round(costDataPeak + costDataOffPeak + costDataShoulder, 2),
            current + "_cost_generation": abs(costDataGeneration),
            current + "_suburb_average": suburbAverage,
            current + "_cost_difference": costDifference,
            current + "_difference_message": costDifferenceMessage['text'],
            current + "_percentage_difference": kwhPercentageDifference,
            current + "_consumption_difference": round(netConsumption - previousPeriodNetConsumption, 3),
            current + "_consumption_change": costDifferenceMessage['change'],

            previous + "_usage": round(previousPeriodPeakConsumption + previousPeriodOffPeakConsumption + previousPeriodShoulderConsumption - previousPeriodGeneration, 3),
            previous + "_consumption": round(previousPeriodPeakConsumption + previousPeriodOffPeakConsumption + previousPeriodShoulderConsumption, 3),
            previous + "_generation": previousPeriodGeneration
            }
        return period_data


    def _sum_period_array(self, json_array_of_value, rounding_digits):
        total_value = 0.0
        for value in json_array_of_value:
            if value is not None:
                if type(value) is dict:
                    total_value += value['total']
                else:
                    total_value += value
        return round(total_value, rounding_digits)


    def _strip_currency(self, amount):
        import locale
        return locale.atof(amount.strip('$'))


    def fetch_data(self):
        """Get the latest data from Energy Easy."""
        
        # setup requests session
        self._session = requests.Session()

        # Get login page
        login_url = self._get_login_page()
        
        # Post login page
        self._post_login_page(login_url)

        self._data.update(self._get_tariffs())

        # Get Daily Usage data
        self._data.update(self._get_daily_data(1))

        # Get Daily Usage data
        self._data.update(self._get_weekly_data(0))

        # Get Daily Usage data
        self._data.update(self._get_monthly_data(0))


    def get_data(self):
        return self._data
