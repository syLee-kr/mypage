document.addEventListener('DOMContentLoaded', function () {
    console.log("DOMContentLoaded 이벤트 발생");

    const calendarEl = document.getElementById('calendar');

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        locale: 'ko',
        selectable: userRole === 'admin',
        editable: userRole === 'admin',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: function (fetchInfo, successCallback, failureCallback) {
            axios.get('/api/calendar/events', {
                params: {
                    start: fetchInfo.startStr,
                    end: fetchInfo.endStr
                }
            })
                .then(response => {
                    console.log("Received events:", response.data);
                    if (!Array.isArray(response.data)) {
                        console.error("Expected an array of events");
                        failureCallback(new Error("Invalid events format"));
                        return;
                    }
                    const events = response.data.map(event => {
                        // 시작 날짜와 종료 날짜를 정확히 변환
                        const startDate = new Date(event.start_date);
                        const endDate = new Date(event.end_date);

                        // endDate에 하루를 추가
                        endDate.setDate(endDate.getDate() + 1);

                        return {
                            id: event._id,
                            title: event.title,
                            start: startDate,
                            end: endDate, // 수정된 endDate
                            description: event.description,
                            type: event.type,
                            allDay: true,
                            classNames: ['multi-day-event', event.type] // 타입별 CSS 클래스 추가
                        };
                    });
                    console.log("Mapped events:", events);
                    successCallback(events);
                })
                .catch(error => {
                    console.error("Error fetching events:", error);
                    failureCallback(error);
                });
        },
        eventClick: function (info) {
            if (userRole !== 'admin') {
                console.log("관리자가 아니므로 수정 불가.");
                return;
            }
            openEditModal(info.event);
        },
        dateClick: function (info) {
            if (userRole !== 'admin') {
                console.log("관리자가 아니므로 추가 불가.");
                return;
            }
            openAddModal(info.dateStr);
        },
        eventDidMount: function (info) {
            console.log("Rendered Event:", info.event);
            // CSS 클래스가 이미 추가되어 있으므로 추가 스타일은 불필요
        },
    });

    calendar.render();

    // 모달 관련 요소
    const modal = document.getElementById('event-modal');
    const closeButton = document.querySelector('.close-button');
    const modalTitle = document.getElementById('modal-title');
    const eventForm = document.getElementById('event-form');
    const saveButton = document.getElementById('save-event-button');
    const deleteButton = document.getElementById('delete-event-button');

    let currentEvent = null;

    function openAddModal(dateStr) {
        modalTitle.textContent = '이벤트 추가';
        eventForm.reset();
        document.getElementById('start_date').value = dateStr;
        document.getElementById('end_date').value = dateStr;
        currentEvent = null;
        deleteButton.style.display = 'none';
        modal.classList.add('active');
    }

    function openEditModal(event) {
        modalTitle.textContent = '이벤트 수정';
        eventForm.reset();
        document.getElementById('title').value = event.title;
        document.getElementById('description').value = event.extendedProps.description || '';
        document.getElementById('start_date').value = formatDate(event.start);
        document.getElementById('end_date').value = formatDate(event.end);
        if (userRole === 'admin') {
            document.getElementById('type').value = event.extendedProps.type || 'event';
        }
        currentEvent = event;
        deleteButton.style.display = 'block';
        modal.classList.add('active');
    }

    function formatDate(date) {
        const pad = (n) => (n < 10 ? '0' + n : n);
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
    }

    closeButton.addEventListener('click', function () {
        modal.classList.remove('active');
        deleteButton.style.display = 'none';
    });

    window.addEventListener('click', function (event) {
        if (event.target === modal) {
            modal.classList.remove('active');
            deleteButton.style.display = 'none';
        }
    });

    eventForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const formData = new FormData(eventForm);
        const data = {
            title: formData.get('title'),
            description: formData.get('description'),
            start_date: formData.get('start_date'),
            end_date: formData.get('end_date')
        };

        if (userRole === 'admin') {
            data.type = formData.get('type');
        }

        if (currentEvent) {
            axios.put(`/api/calendar/${currentEvent.id}/edit`, data)
                .then(response => {
                    calendar.refetchEvents();
                    modal.classList.remove('active');
                    deleteButton.style.display = 'none';
                    alert(response.data.message);
                })
                .catch(error => {
                    alert(error.response?.data?.detail || '이벤트 수정 실패');
                });
        } else {
            axios.post('/api/calendar/create', data)
                .then(response => {
                    calendar.refetchEvents();
                    modal.classList.remove('active');
                    alert(response.data.message);
                })
                .catch(error => {
                    alert(error.response?.data?.detail || '이벤트 추가 실패');
                });
        }
    });

    deleteButton.addEventListener('click', function () {
        if (currentEvent) {
            if (confirm('이벤트를 삭제하시겠습니까?')) {
                axios.delete(`/api/calendar/${currentEvent.id}`)
                    .then(response => {
                        calendar.refetchEvents();
                        modal.classList.remove('active');
                        deleteButton.style.display = 'none';
                        alert(response.data.message);
                    })
                    .catch(error => {
                        alert(error.response?.data?.detail || '이벤트 삭제 실패');
                    });
            }
        }
    });
});
