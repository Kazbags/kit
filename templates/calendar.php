
{% extends "layout.html" %}

{% block title %}
    calendar
{% endblock %}
{% block head %}
<link href='https://use.fontawesome.com/releases/v5.0.6/css/all.css' rel='stylesheet'>
<link href='/static/theme/bootstrap.min.css' rel='stylesheet'>
{% endblock %}
{% block main %}
<style>
.fc-day-grid-event > .fc-content {
    white-space: pre-line;
}
</style>

<div class="calendar-container">
 <div id="calendar"></div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', function() {
  var calendarEl = document.getElementById('calendar');

  var calendar = new FullCalendar.Calendar(calendarEl, {
    plugins: [ 'dayGrid', 'timeGrid', 'list', 'bootstrap', 'interaction'],
    timeZone: 'Europe/London',
    themeSystem: 'bootstrap',
    header: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,dayGridWeek,dayGridDay,listMonth'
    },

    weekNumbers: true,
    eventLimit: false, // allow "more" link when too many events
    events: {{ events }},
    eventRender: function(info) {
      var tooltip = new Tooltip(info.el, {
        title: info.event.title,
        placement: 'top',
        trigger: 'hover',
        container: 'body'
      });
    },

  });


  calendar.render();
});
</script>



{% endblock %}
