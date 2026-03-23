import { useState } from 'react'
import { useLocalStorage } from '../../hooks/useLocalStorage.js'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December',
]

function getDaysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year, month) {
  return new Date(year, month, 1).getDay()
}

export default function CalendarPanel() {
  const today = new Date()
  const [viewYear, setViewYear] = useState(today.getFullYear())
  const [viewMonth, setViewMonth] = useState(today.getMonth())
  const [selected, setSelected] = useState(null)
  const [events, setEvents] = useLocalStorage('oa_events', [])
  const [newEvent, setNewEvent] = useState({ title: '', time: '' })

  const prevMonth = () => {
    if (viewMonth === 0) { setViewYear(y => y - 1); setViewMonth(11) }
    else setViewMonth(m => m - 1)
  }

  const nextMonth = () => {
    if (viewMonth === 11) { setViewYear(y => y + 1); setViewMonth(0) }
    else setViewMonth(m => m + 1)
  }

  const daysInMonth = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth)
  const daysInPrevMonth = getDaysInMonth(viewYear, viewMonth - 1)

  // Build grid cells
  const cells = []
  // Previous month tail
  for (let i = firstDay - 1; i >= 0; i--) {
    cells.push({ day: daysInPrevMonth - i, currentMonth: false, year: viewMonth === 0 ? viewYear - 1 : viewYear, month: viewMonth === 0 ? 11 : viewMonth - 1 })
  }
  // Current month
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ day: d, currentMonth: true, year: viewYear, month: viewMonth })
  }
  // Next month head
  const remaining = 42 - cells.length
  for (let d = 1; d <= remaining; d++) {
    cells.push({ day: d, currentMonth: false, year: viewMonth === 11 ? viewYear + 1 : viewYear, month: viewMonth === 11 ? 0 : viewMonth + 1 })
  }

  const dateKey = (y, m, d) => `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`

  const eventsForDate = (y, m, d) => events.filter(e => e.date === dateKey(y, m, d))

  const isToday = (y, m, d) =>
    y === today.getFullYear() && m === today.getMonth() && d === today.getDate()

  const isSelected = (y, m, d) =>
    selected && selected.year === y && selected.month === m && selected.day === d

  const selectDay = (cell) => {
    setSelected(cell)
    setNewEvent({ title: '', time: '' })
  }

  const addEvent = (e) => {
    e.preventDefault()
    if (!newEvent.title.trim() || !selected) return
    setEvents(prev => [
      ...prev,
      {
        id: Date.now(),
        title: newEvent.title.trim(),
        time: newEvent.time,
        date: dateKey(selected.year, selected.month, selected.day),
      },
    ])
    setNewEvent({ title: '', time: '' })
  }

  const deleteEvent = (id) => {
    setEvents(prev => prev.filter(e => e.id !== id))
  }

  const selectedEvents = selected
    ? eventsForDate(selected.year, selected.month, selected.day)
    : []

  const selectedLabel = selected
    ? `${MONTHS[selected.month]} ${selected.day}, ${selected.year}`
    : null

  return (
    <>
      <div className="panel-header">
        <span>📅</span>
        <h1>Calendar</h1>
      </div>

      <div className="panel-body">
        {/* Month navigation */}
        <div className="calendar-grid-header">
          <button className="calendar-nav-btn" onClick={prevMonth}>‹</button>
          <h2>{MONTHS[viewMonth]} {viewYear}</h2>
          <button className="calendar-nav-btn" onClick={nextMonth}>›</button>
        </div>

        {/* Weekday headers */}
        <div className="calendar-weekdays">
          {WEEKDAYS.map(d => (
            <div key={d} className="calendar-weekday">{d}</div>
          ))}
        </div>

        {/* Day grid */}
        <div className="calendar-days">
          {cells.map((cell, i) => {
            const dayEvents = eventsForDate(cell.year, cell.month, cell.day)
            return (
              <div
                key={i}
                className={`calendar-day
                  ${!cell.currentMonth ? 'other-month' : ''}
                  ${isToday(cell.year, cell.month, cell.day) ? 'today' : ''}
                  ${isSelected(cell.year, cell.month, cell.day) ? 'selected' : ''}
                `}
                onClick={() => selectDay(cell)}
              >
                <span className="day-num">{cell.day}</span>
                {dayEvents.length > 0 && (
                  <div className="day-dots">
                    {dayEvents.slice(0, 3).map(e => (
                      <span key={e.id} className="day-dot" />
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Selected day events */}
        {selected && (
          <div className="event-panel">
            <h3>📅 {selectedLabel}</h3>

            {selectedEvents.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
                No events — add one below.
              </p>
            ) : (
              selectedEvents.map(ev => (
                <div key={ev.id} className="event-item">
                  <span className="event-dot" />
                  <span className="event-title">{ev.title}</span>
                  {ev.time && <span className="event-time">{ev.time}</span>}
                  <button className="event-delete" onClick={() => deleteEvent(ev.id)}>×</button>
                </div>
              ))
            )}

            <form onSubmit={addEvent} style={{ marginTop: 12 }}>
              <div className="form-row cols-2" style={{ marginBottom: 8 }}>
                <div className="field">
                  <input
                    value={newEvent.title}
                    onChange={e => setNewEvent(n => ({ ...n, title: e.target.value }))}
                    placeholder="Event title"
                  />
                </div>
                <div className="field">
                  <input
                    type="time"
                    value={newEvent.time}
                    onChange={e => setNewEvent(n => ({ ...n, time: e.target.value }))}
                  />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={!newEvent.title.trim()}>
                + Add Event
              </button>
            </form>
          </div>
        )}
      </div>
    </>
  )
}
