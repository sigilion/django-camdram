from django.conf import settings
import math
import datetime
from django import template
from django.template.loader import get_template

def fits(diary_row, performance):
    for p in diary_row:
        if p.start_date < performance.end_date and p.end_date > performance.start_date:
            return False
    return True


def box_pack(events, week):
    """
    Events should be a queryset with start_date, end_date, time and show fields, week
    should be a datetime.date object of a day in the week
    Returns a list of rows, each row is a list of events.
    """
    week_start = datetime.date.fromordinal(week.toordinal() - week.weekday())
    week_end = datetime.date.fromordinal(week.toordinal() - week.weekday() + 6)
    events = events.filter(end_date__gte=week_start).filter(start_date__lte=week_end)
    row_height = settings.DRAMA_DIARY_ROW_HEIGHT
    row_timedelta = datetime.timedelta(minutes=row_height)
    time_rows = [] #these rows contain all performances in a timeslot, may be rendered as multiple iary rows
    packed = []
    for i in range(math.ceil(24*60/row_height)):
        start_time = (datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0, 0, 0)) + i*row_timedelta).time()
        end_datetime = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0, 0, 0)) + (i+1)*row_timedelta
        if end_datetime.date() == datetime.date.today():
            end_time = end_datetime.time()
        else:
            end_time = datetime.time.max
        row_events = events.filter(time__lt=end_time).filter(time__gte=start_time)
        time_rows.append(row_events)
    for row in time_rows:
        performances = list(row.order_by('venue', 'time'))
        while len(performances) > 0:
            diary_row = []
            for performance in performances.copy():
                if fits(diary_row, performance):
                    diary_row.append(performance)
                    performances.remove(performance)
            packed.append(diary_row)
    return packed

class DiaryEvent:
    def __init__(self, performance, days, skip):
        self.performance = performance
        self.days = days
        self.skip = skip
        
    performance = None
    days = None
    skip = None

def diary_row(events, start_date, row_template):
    events = sorted(events, key=lambda x: x.start_date)
    end_date = start_date + datetime.timedelta(days=6)
    last_date = start_date - datetime.timedelta(days=1)
    diary_events = []
    for event in events:
        days = (min(end_date, event.end_date) - max(event.start_date, start_date)).days + 1
        skip = (event.start_date - last_date).days - 1
        diary_events.append(DiaryEvent(performance=event, days=days, skip=skip))
        last_date = min(end_date, event.end_date)
    return row_template.render(template.Context({'events': diary_events}))

def diary_week(events, week, week_template, row_template):
    #TODO: Label
    """
    Events is a queryset of events, week is a datetime.date within the week,
    week_template and row_template are self explanitory.
    """
    start_date = datetime.date.fromordinal(week.toordinal() - week.weekday())
    end_date = datetime.date.fromordinal(week.toordinal() - week.weekday() + 6)
    packed = box_pack(events, start_date)
    dates = []
    for i in range(7):
        dates.append(start_date + datetime.timedelta(days=i))
    rows = []
    for row in packed:
        rows.append(diary_row(row, start_date, row_template))
    return week_template.render(template.Context({'dates':dates, 'rows':rows, 'start_date': start_date, 'end_date': end_date}))

def diary(start_date, end_date, events):
    diary_week_template = get_template('drama/diary_week.html')
    diary_row_template = get_template('drama/diary_row.html')
    diary = '<div id="diary">'
    for i in range(math.ceil((end_date - start_date).days/7)):
        week = diary_week(events, start_date + datetime.timedelta(days=7*i), diary_week_template, diary_row_template)
        diary = '\n'.join([diary, week])
    return '\n'.join([diary, "</div>"])
