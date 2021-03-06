from __future__ import absolute_import
import re

import regrws.payload
import regrws.restful

class DictFromTemplate(object):

    """Class for method object for converting a template to a dict."""

    _regex = re.compile(r'\d\d\.(.*):(.*)')

    def __init__(self, template):
        """Return a DictFromTemplate object that will convert the
        template string to a dict.
        """

        self.template = template
        self.parsed_template = {}

    def run(self):
        """Return dict containing parsed contents of template string.

        All dict item values are lists because template field labels
        (used for dict keys) can be repeated. The returned dict is
        suitable for use with PayloadFromTemplateDict.
        """

        for line in self.template:
            match = self._regex.match(line)
            if match:
                self._process(match)
        return self.parsed_template

    def _process(self, m):
        # Create/modify dict item
        key = m.group(1).strip()
        value = m.group(2).strip()
        if key in self.parsed_template:
            self.parsed_template[key].append(value)
        else:
            self.parsed_template[key] = [value]

class _PayloadFromDict(object):

    """Abstract class for method object for converting a dict to a
    payload.
    """

    # The following class attributes are overridden in subclasses.
    _handler = {}  # map of dict keys to handler method names
    _attr = {}  # map of dict keys to payload's simple list attributes
    _ignore = ()  # dict keys to ignore (not used in payload)

    def __init__(self, source, target):
        """Return a PayloadFromDict object that will convert the
        source dict to a payload of the target class.

        All values of dict items are expected to be lists.
        """

        self._verify_class_dicts()
        self.source = source
        # this relies on payload module names matching payload class names
        self.module = getattr(regrws.payload, target.__module__.split('.')[-1])
        self.payload = target()

    def _verify_class_dicts(self):
        # ensure at least one required class dict is not empty
        if not (self._handler or self._attr):
            msg = '_handler or _attr must be populated in derived classes'
            # not the most appropriate exception
            raise NotImplementedError(msg)

    def run(self):
        """Return payload built from dict."""

        for key, value in self.source.iteritems():
            if key in self._handler:
                # call the corresponding handler
                method = getattr(self, self._handler[key])
                method(value)
            elif key in self._attr:
                self._assign(self._attr[key], value)
            elif key in self._ignore:
                continue
            else:
                raise regrws.restful.RegRwsError('%s has no attribute corresponding to key %s' % (self.payload.__class__, key))
        return self.payload

    def _assign(self, attr, value):
        # assign value to attribute if payload has that attribute
        self._verify_attribute(attr)
        setattr(self.payload, attr, value)

    def _contact_type(self, value):
        self._verify_attribute('contactType')
        if value == ['P']:
            self.payload.contactType = ['PERSON']
        elif value == ['R']:
            self.payload.contactType = ['ROLE']

    def _address(self, value):
        if not self.payload.streetAddress:
            self.payload.streetAddress = [self.module.streetAddress()]
        for count, line in enumerate(value):
            self.payload.streetAddress[0].add_line(self.module.line(count,
                                                                    line))

    def _comment(self, value):
        if not self.payload.comment:
            self.payload.comment = [self.module.comment()]
        for count, line in enumerate(value):
            self.payload.comment[0].add_line(self.module.line(count, line))

    def _country_code(self, value):
        iso3166_1 = self.module.iso3166_1(code2=value)
        self.payload.iso3166_1 = [iso3166_1]

    def _phone_office(self, value):
        self._phone(value, 'O')

    def _phone_mobile(self, value):
        self._phone(value, 'M')

    def _phone_fax(self, value):
        self._phone(value, 'F')

    def _phone(self, value, type_code):
        if not self.payload.phones:
            self.payload.phones = [self.module.phones()]
        type_ = [self.module.type_(code=[type_code])]
        self.payload.phones[0].add_phone(self.module.phone(number=value,
                                                           type_=type_))

    def _poc_admin(self, value):
        self._poc(value, 'AD')

    def _poc_tech(self, value):
        self._poc(value, 'T')

    def _poc_abuse(self, value):
        self._poc(value, 'AB')

    def _poc_noc(self, value):
        self._poc(value, 'N')

    def _poc(self, value, function):
        if not self.payload.pocLinks:
            self.payload.pocLinks = [self.module.pocLinks()]
        self.payload.pocLinks[0].add_pocLinkRef(self.module.pocLinkRef(function,
                                                                       value[0]))

    def _office_extension(self, value):
        for phone in self.payload.phones[0].phone:
            if phone.type_[0].code[0] == 'O':
                phone.extension = value

    def _email_address(self, value):
        if not self.payload.emails:
            self.payload.emails = [self.module.emails()]
        for email in value:
            self.payload.emails[0].add_email(email)

    def _verify_attribute(self, attr):
        # source dict should not contain keys that do not correspond to
        # input target class's data attributes (except for those in
        # the ignore list).
        if getattr(self.payload, attr, None) is None:
            raise regrws.restful.RegRwsError('%s does not have attribute %s' %
                                             (self.payload.__class__, attr))

class PayloadFromTemplateDict(_PayloadFromDict):

    """Method object for converting a template dict to a payload."""

    # map of dict keys to handler method names
    _handler = {'Contact Type (P or R)': '_contact_type',
                'Address': '_address',
                'Country Code': '_country_code',
                'Office Phone Number': '_phone_office',
                'Office Phone Number Extension': '_office_extension',
                'E-mail Address': '_email_address',
                'Mobile': '_phone_mobile',
                'Fax': '_phone_fax',
                'Public Comments': '_comment',
                'Org Address': '_address',
                'Org Country Code': '_country_code',
                'Admin POC Handle': '_poc_admin',
                'Tech POC Handle': '_poc_tech',
                'Abuse POC Handle': '_poc_abuse',
                'NOC POC Handle': '_poc_noc'}
    # map of dict keys to payload's simple list attributes
    _attr = {'Last Name or Role Account': 'lastName',
             'First Name': 'firstName',
             'Middle Name': 'middleName',
             'Company Name': 'companyName',
             'City': 'city',
             'State/Province': 'iso3166_2',
             'Postal Code': 'postalCode',
             "Organization's Legal Name": 'orgName',
             "Organization's D/B/A": 'dbaName',
             'Business Tax ID Number (DO NOT LIST SSN)': 'taxId',
             'Org City': 'city',
             'Org State/Province': 'iso3166_2',
             'Org Postal Code': 'postalCode'}
    # dict keys to ignore (not used in payload)
    _ignore = ('API Key',
               'Registration Action (N,M, or R)',
               'Existing POC Handle',
               'Existing OrgID',
               'Referral Server',
               'Additional Information')
