# Copyright 2013 Mathias WOLFF
# This file is part of pyfreebilling.
# 
# pyfreebilling is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# pyfreebilling is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with pyfreebilling.  If not, see <http://www.gnu.org/licenses/>

from django.conf import settings
from common.common_functions import variable_value, ceil_strdate
from datetime import datetime


def cdr_record_common_fun(request):
    """Return Form with Initial data or Array (kwargs) for Voipcall_Report
Changelist_view"""
    start_date = ''
    end_date = ''
    if request.POST.get('from_date'):
        from_date = request.POST.get('from_date')
        start_date = ceil_strdate(from_date, 'start')

    if request.POST.get('to_date'):
        to_date = request.POST.get('to_date')
        end_date = ceil_strdate(to_date, 'end')

    # Assign form field value to local variable
    disposition = variable_value(request, 'status')
    campaign_id = variable_value(request, 'campaign')

    kwargs = {}
    if start_date and end_date:
        kwargs['starting_date__range'] = (start_date, end_date)
    if start_date and end_date == '':
        kwargs['starting_date__gte'] = start_date
    if start_date == '' and end_date:
        kwargs['starting_date__lte'] = end_date

    if disposition and disposition != 'all':
        kwargs['disposition__exact'] = disposition

    if campaign_id and campaign_id != '0':
        kwargs['callrequest__campaign_id'] = campaign_id

    if len(kwargs) == 0:
        tday = datetime.today()
        kwargs['starting_date__gte'] = datetime(tday.year,
                                                tday.month,
                                                tday.day, 0, 0, 0, 0)
        kwargs['starting_date__lte'] = datetime(tday.year,
                                                tday.month,
                                                tday.day, 23, 59, 59)
    return kwargs


def return_query_string(query_string, para):
    """
Function is used in voipcall_search_admin_form_fun

>>> return_query_string('key=1', 'key_val=apple')
'key=1&key_val=apple'
>>> return_query_string(False, 'key_val=apple')
'key_val=apple'
"""
    if query_string:
        query_string += '&%s' % (para)
    else:
        query_string = para
    return query_string


def cdr_search_admin_form_fun(request):
    """Return query string for Voipcall_Report Changelist_view"""
    start_date = ''
    end_date = ''
    if request.POST.get('from_date'):
        start_date = request.POST.get('from_date')

    if request.POST.get('to_date'):
        end_date = request.POST.get('to_date')

    # Assign form field value to local variable
    disposition = variable_value(request, 'status')
    campaign_id = variable_value(request, 'campaign')
    query_string = ''

    if start_date and end_date:
        date_string = 'starting_date__gte=' + start_date + \
            '&starting_date__lte=' + end_date + '+23%3A59%3A59'
        query_string = return_query_string(query_string, date_string)

    if start_date and end_date == '':
        date_string = 'starting_date__gte=' + start_date
        query_string = return_query_string(query_string, date_string)

    if start_date == '' and end_date:
        date_string = 'starting_date__lte=' + end_date
        query_string = return_query_string(query_string, date_string)

    if disposition and disposition != 'all':
        disposition_string = 'disposition__exact=' + disposition
        query_string = return_query_string(query_string, disposition_string)

    if campaign_id and campaign_id != '0':
        campaign_string = 'callrequest__campaign_id=' + str(campaign_id)
        query_string = return_query_string(query_string, campaign_string)

    if start_date == '' and end_date == '':
        tday = datetime.today()
        end_date = start_date = tday.strftime("%Y-%m-%d")
        date_string = 'starting_date__gte=' + start_date + \
            '&starting_date__lte=' + end_date + '+23%3A59%3A59'
        query_string = return_query_string(query_string, date_string)

    return query_string


