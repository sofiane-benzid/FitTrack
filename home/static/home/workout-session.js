
console.log('workout-session.js loaded at:', new Date().toISOString());

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded at:', new Date().toISOString());

    let startTime = Date.now();
    let timerInterval;
    const timerDisplay = document.querySelector('.workout-timer');

    function startTimer() {
        timerInterval = setInterval(() => {
            const elapsedTime = Date.now() - startTime;
            const hours = Math.floor(elapsedTime / 3600000);
            const minutes = Math.floor((elapsedTime % 3600000) / 60000);
            const seconds = Math.floor((elapsedTime % 60000) / 1000);
            timerDisplay.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }, 1000);
    }

    function createExerciseHTML(exercise, index) {
        if (workoutType === 'Running') {
            return `
                <div class="exercise-card">
                    <div class="exercise-header">
                        <h2>${exercise.name}</h2>
                    </div>
                    <div class="run-tracking">
                        <div class="input-group">
                            <label>Distance (km)</label>
                            <input type="number" step="0.01" min="0" class="distance-input" placeholder="Enter distance" value="${exercise.sets[0].distance}">
                            <button class="reset-template-button">Reset to Template</button>
                        </div>
                        <div class="previous-data">
                            <p>${exercise.sets[0].previous}</p>
                        </div>
                    </div>
                </div>
            `;
        }

        const columnHeaders = `
            <div class="exercise-set column-headers">
                <div class="set-number">Set</div>
                <div class="previous-result">Previous</div>
                <div class="current-set">
                    <div class="input-header">Weight (kg)</div>
                    <div class="input-header">Reps</div>
                </div>
                <div class="complete-header">Done</div>
            </div>
        `;

        const setsHTML = exercise.sets.map((set, setIndex) => `
            <div class="exercise-set ${set.completed ? 'completed' : ''}">
                <div class="set-number">${setIndex + 1}</div>
                <div class="previous-result">${set.previous}</div>
                <div class="current-set">
                    <input type="number" placeholder="Weight (kg)" class="weight-input" value="${set.weight}" data-exercise="${index}" data-set="${setIndex}">
                    <input type="number" placeholder="Reps" class="reps-input" value="${set.reps}" data-exercise="${index}" data-set="${setIndex}">
                    <button class="remove-set-btn" onclick="removeSet(${index}, ${setIndex})">🗑️</button>
                </div>
                <button class="complete-set ${set.completed ? 'completed' : ''}" data-exercise="${index}" data-set="${setIndex}">✓</button>
            </div>
        `).join('');

        return `
            <div class="exercise-card">
                <div class="exercise-header">
                    <div class="exercise-name">
                        <h2 class="exercise-title">${exercise.name}</h2>
                        <button class="edit-name-button">✏️</button>
                    </div>
                    <button class="remove-exercise-btn" onclick="removeExercise(${index})">🗑️</button>                    
                </div>
                ${columnHeaders}
                <div class="exercise-sets">
                    ${setsHTML}
                </div>
                <div class="exercise-footer">
                    <button class="add-set-button" onclick="addSet(${index})">+ Add Set</button>
                </div>
            </div>
        `;
    }

    function initializeWorkout() {
        document.getElementById('workoutTitle').textContent = workoutData.title;
        const exerciseCountElement = document.getElementById('exerciseCount');
        const setCountElement = document.getElementById('setCount');
        if (exerciseCountElement && setCountElement) {
            exerciseCountElement.textContent = `${workoutData.exercises.length} exercises`;
            const totalSets = workoutData.exercises.reduce((total, exercise) => total + exercise.sets.length, 0);
            setCountElement.textContent = `${totalSets} sets`;
        }

        const exerciseList = document.getElementById('sessionExercises');
        workoutData.exercises.forEach((exercise, index) => {
            exercise.sets.forEach(set => {
                if (typeof set.completed === 'undefined') set.completed = false;
            });
            exerciseList.insertAdjacentHTML('beforeend', createExerciseHTML(exercise, index));
        });
        if (workoutType === 'Gym Session') {
            document.getElementById('addExerciseContainer').classList.remove('hidden');
        }
    }

    window.addSet = function(exerciseIndex) {
        const exercise = workoutData.exercises[exerciseIndex];
        const setNumber = exercise.sets.length + 1;
        exercise.sets.push({ previous: "New Set", weight: "", reps: "", completed: false });

        const exerciseCard = document.querySelectorAll('.exercise-card')[exerciseIndex];
        const setsContainer = exerciseCard.querySelector('.exercise-sets');

        const newSetHTML = `
            <div class="exercise-set">
                <div class="set-number">${setNumber}</div>
                <div class="previous-result">New Set</div>
                <div class="current-set">
                    <input type="number" placeholder="Weight (kg)" class="weight-input" value="" data-exercise="${exerciseIndex}" data-set="${setNumber - 1}">
                    <input type="number" placeholder="Reps" class="reps-input" value="" data-exercise="${exerciseIndex}" data-set="${setNumber - 1}">
                    <button class="remove-set-btn" onclick="removeSet(${exerciseIndex}, ${setNumber - 1})">🗑️</button>
                </div>
                <button class="complete-set" data-exercise="${exerciseIndex}" data-set="${setNumber - 1}">✓</button>
            </div>
        `;

        setsContainer.insertAdjacentHTML('beforeend', newSetHTML);
        updateSetCount();
    };

    window.removeExercise = function(exerciseIndex) {
        if (confirm('Are you sure you want to remove this exercise?')) {
            workoutData.exercises.splice(exerciseIndex, 1);
            const exerciseList = document.getElementById('sessionExercises');
            exerciseList.innerHTML = '';
            workoutData.exercises.forEach((exercise, index) => {
                exerciseList.insertAdjacentHTML('beforeend', createExerciseHTML(exercise, index));
            });
            document.getElementById('exerciseCount').textContent = `${workoutData.exercises.length} exercises`;
            updateSetCount();
        }
    };

    window.removeSet = function(exerciseIndex, setIndex) {
        const exercise = workoutData.exercises[exerciseIndex];
        exercise.sets.splice(setIndex, 1);
        const exerciseCard = document.querySelectorAll('.exercise-card')[exerciseIndex];
        const setsContainer = exerciseCard.querySelector('.exercise-sets');
        setsContainer.innerHTML = exercise.sets.map((set, idx) => `
            <div class="exercise-set ${set.completed ? 'completed' : ''}">
                <div class="set-number">${idx + 1}</div>
                <div class="previous-result">${set.previous}</div>
                <div class="current-set">
                    <input type="number" placeholder="Weight (kg)" class="weight-input" value="${set.weight}" data-exercise="${exerciseIndex}" data-set="${idx}">
                    <input type="number" placeholder="Reps" class="reps-input" value="${set.reps}" data-exercise="${exerciseIndex}" data-set="${idx}">
                    <button class="remove-set-btn" onclick="removeSet(${exerciseIndex}, ${idx})">🗑️</button>
                </div>
                <button class="complete-set ${set.completed ? 'completed' : ''}" data-exercise="${exerciseIndex}" data-set="${idx}">✓</button>
            </div>
        `).join('');
        updateSetCount();
    };

    function updateSetCount() {
        const totalSets = workoutData.exercises.reduce((total, exercise) => total + exercise.sets.length, 0);
        document.getElementById('setCount').textContent = `${totalSets} sets`;
    }

    document.querySelector('.add-exercise-button')?.addEventListener('click', () => {
        console.log('Add Exercise button clicked');
        const newExercise = {
            name: "New Exercise",
            sets: [{ previous: "New Set", weight: "", reps: "", completed: false }]
        };
        workoutData.exercises.push(newExercise);
        const exerciseList = document.getElementById('sessionExercises');
        exerciseList.insertAdjacentHTML('beforeend', createExerciseHTML(newExercise, workoutData.exercises.length - 1));
        document.getElementById('exerciseCount').textContent = `${workoutData.exercises.length} exercises`;
        updateSetCount();
    });

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('complete-set')) {
            const button = e.target;
            const exerciseIndex = parseInt(button.dataset.exercise);
            const setIndex = parseInt(button.dataset.set);
            const set = workoutData.exercises[exerciseIndex].sets[setIndex];
            set.completed = !set.completed;
            button.classList.toggle('completed', set.completed);
            // Toggle .completed on the parent .exercise-set row
            const setRow = button.closest('.exercise-set');
            setRow.classList.toggle('completed', set.completed);
            console.log(`Set ${setIndex + 1} of exercise ${exerciseIndex} toggled to: ${set.completed}`);
        }
    });

    document.addEventListener('input', (e) => {
        if (e.target.classList.contains('weight-input') || e.target.classList.contains('reps-input')) {
            const exerciseIndex = parseInt(e.target.dataset.exercise);
            const setIndex = parseInt(e.target.dataset.set);
            const exercise = workoutData.exercises[exerciseIndex];
            const set = exercise.sets[setIndex];

            if (e.target.classList.contains('weight-input')) {
                set.weight = e.target.value ? parseFloat(e.target.value) : "";
            } else if (e.target.classList.contains('reps-input')) {
                set.reps = e.target.value ? parseInt(e.target.value) : "";
            }
        } else if (e.target.classList.contains('distance-input')) {
            workoutData.exercises[0].sets[0].distance = e.target.value ? parseFloat(e.target.value) : "";
        }
    });

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('reset-template-button')) {
            const distanceInput = document.querySelector('.distance-input');
            distanceInput.value = workoutData.template_distance || "";
            workoutData.exercises[0].sets[0].distance = workoutData.template_distance || "";
        }
    });

    document.querySelector('.finish-workout-button').addEventListener('click', (e) => {
        e.preventDefault();
        console.log('Finish button clicked, workoutType:', workoutType);
        clearInterval(timerInterval);
        const elapsedTime = Date.now() - startTime;
        const durationSeconds = Math.floor(elapsedTime / 1000);

        if (workoutType === 'Running') {
            const distance = workoutData.exercises[0].sets[0].distance;
            const payload = {
                template_id: workoutData.template_id,
                activity_type: 'R',
                distance: distance,
                duration_seconds: durationSeconds,
            };
            console.log('Sending running session data:', JSON.stringify(payload, null, 2));
            fetch('/home/finish-workout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(payload),
            })
                .then(response => response.json())
                .then(data => {
                    console.log('Response:', data);
                    if (data.status === 'success') {
                        window.location.href = data.redirect_url;
                    } else {
                        alert('Error saving workout: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while saving the workout.');
                });
        } else if (workoutType === 'Gym Session') {
            const payload = {
                template_id: workoutData.template_id,
                activity_type: 'G',
                duration_seconds: durationSeconds,
                exercises: workoutData.exercises.map(exercise => ({
                    name: exercise.name,
                    sets: exercise.sets.map(set => ({
                        weight: set.weight,
                        reps: set.reps,
                        completed: set.completed
                    }))
                }))
            };
            console.log('Sending gym session data:', JSON.stringify(payload, null, 2));
            fetch('/home/finish-workout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(payload),
            })
                .then(response => response.json())
                .then(data => {
                    console.log('Response:', data);
                    if (data.status === 'success') {
                        window.location.href = data.redirect_url;
                    } else {
                        alert('Error saving workout: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while saving the workout.');
                });
        }
    });

    function getCsrfToken() {
        return csrfToken;
    }

    initializeWorkout();
    startTimer();

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('edit-name-button')) {
            const header = e.target.closest('.exercise-name');
            const title = header.querySelector('.exercise-title');
            const currentName = title.textContent;

            const input = document.createElement('input');
            input.type = 'text';
            input.value = currentName;
            input.className = 'exercise-name-input';

            title.style.display = 'none';
            e.target.style.display = 'none';
            header.insertBefore(input, title);
            input.focus();

            input.addEventListener('blur', () => {
                const newName = input.value.trim();
                if (newName) {
                    title.textContent = newName;
                    const exerciseIndex = Array.from(document.querySelectorAll('.exercise-card')).indexOf(header.closest('.exercise-card'));
                    workoutData.exercises[exerciseIndex].name = newName;
                }
                title.style.display = '';
                e.target.style.display = '';
                input.remove();
            });

            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    input.blur();
                }
            });
        }
    });
});