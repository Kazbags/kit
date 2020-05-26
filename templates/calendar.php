
{% extends "layout.html" %}

{% block title %}
    calendar
{% endblock %}

{% block main %}
<style>
.fc-day-grid-event > .fc-content {
    white-space: pre-line;
}
</style>

<div class="container">
 <div id="calendar"></div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', function() {
  var calendarEl = document.getElementById('calendar');

  var calendar = new FullCalendar.Calendar(calendarEl, {
    plugins: [ 'dayGrid', 'timeGrid', 'list', 'bootstrap' ],
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

  });

  calendar.render();
});
</script>



{% endblock %}
