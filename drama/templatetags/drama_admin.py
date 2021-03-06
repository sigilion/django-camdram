import string
import math
import itertools
import datetime
import markdown as markdown_lib
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.template.loader import get_template
from guardian.shortcuts import get_users_with_perms, get_groups_with_perms, get_perms_for_model, get_objects_for_user
from django.contrib.auth.models import Permission
from drama.models import Venue
from drama import util

register = template.Library()

class AdminPanelNode(template.Node):
    def __init__(self, item_name):
        self.item_name = item_name
        self.template = get_template('drama/admin_panel.html')
    def render(self, context):
        user = context['user']
        item = context[self.item_name]
        type = item.__class__.__name__.lower()
        if user.has_perm('drama.change_' + type, item):
            subcontext = {}
            subcontext['approved'] = item.approved
            subcontext['type'] = type
            subcontext['item'] = item
            admin_perm = 'change_' + type
            if user.has_perm(admin_perm, item):
                subcontext['admin'] = True
                subcontext['users'] = item.group.user_set.all()
                subcontext['pending_users'] = item.group.pendinggroupmember_set.all()
                subcontext['admin_requests'] = item.get_admin_requests()
                groups = list(get_groups_with_perms(item).exclude(id=item.group.id))
                if type == 'show':
                    for society in item.societies.all():
                        groups = groups + [society.group]
                    for venue in Venue.objects.filter(performance__show=item).distinct():
                        groups = groups + [venue.group]
                subcontext['groups'] = groups
            if user.has_perm('drama.approve_' + type, item):
                subcontext['approve'] = True
            subcontext['staff'] = user.is_staff
            subcontext['csrf_token'] = context['csrf_token']
            return self.template.render(template.Context(subcontext))
        else:
            return ""
        
@register.tag
def admin_panel(parser, token):
    try:
        tag_name, item_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    return AdminPanelNode(item_name)


class DefaultMenuNode(template.Node):
    def __init__(self):
        self.template = get_template('drama/default_menu.html')

    def render(self, context):
        user = context['user']
        approvable = False
        for ctype in ['show','venue','role','person','society']:
            if get_objects_for_user(user,'drama.approve_' + ctype, with_superuser=True, use_groups=True).count() > 0:
                approvable=True
                break;
        subcontext = {
            'add_show':user.has_perm('drama.add_show'),
            'add_venue':user.has_perm('drama.add_venue'),
            'add_role':user.has_perm('drama.add_role'),
            'add_society':user.has_perm('drama.add_society'),
            'view_issues':user.has_perm('issues.view_issues'),
            'view_emaillists':user.has_perm('drama.view_emaillists'),
            'approval_queue':approvable,
            'admin':user.is_staff,
            'csrf_token': context['csrf_token'],
            }
        return self.template.render(template.Context(subcontext))
        
        
@register.tag
def default_menu(parser, token):
    return DefaultMenuNode()

class AdvertLinksNode(template.Node):
    def __init__(self, item_name):
        self.item_name = item_name
        self.template = get_template('drama/advert_links.html')

    def render(self, context):
        user = context['user']
        advert = context[self.item_name]
        if advert.can_edit(user):
            advert = context[self.item_name]
            subcontext = {
                'advert': advert
                }
            return self.template.render(template.Context(subcontext))
        return ''

@register.tag
def advert_links(parser, token):
    try:
        tag_name, item_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    return AdvertLinksNode(item_name)

_the_string = ''.join([string.ascii_uppercase,string.ascii_lowercase])
class AlphabetNode(template.Node):
    def render(self, context):
        if self not in context.render_context:
            context.render_context[self] = itertools.cycle(_the_string)
        alph_iter = context.render_context[self]
        return next(alph_iter)

@register.tag
def alphabet(parser, token):
    return AlphabetNode()
        
    
class DiaryNode(template.Node):
    def __init__(self, item_name):
        self.item_name = item_name

    def render(self, context):
        diary_events = context[self.item_name]
        try:
            start_date = diary_events.order_by('start_date')[0].start_date
            end_date = diary_events.order_by('-end_date')[0].end_date
        except IndexError:
            return ''
        return util.diary(start_date, end_date, diary_events)

@register.tag
def diary(parser, token):
    try:
        tag_name, item_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    return DiaryNode(item_name)


@register.filter(is_safe=True)
@stringfilter
def markdown(value):
    extensions = []

    return mark_safe(markdown_lib.markdown(value,
                                       extensions,
                                       safe_mode='escape',
                                       enable_attributes=False))
