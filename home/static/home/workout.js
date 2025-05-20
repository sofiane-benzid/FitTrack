document.addEventListener('DOMContentLoaded', () => {
    fetch(workoutFormURL)
        .then(response => response.text())
        .then(html => {
            document.getElementById('workoutFormContainer').innerHTML = html;

            const addButton = document.querySelector('.add-button');
            const workoutForm = document.getElementById('workoutForm');
            const workoutType = document.getElementById('workoutType');
            const runFields = document.getElementById('runFields');
            const gymFields = document.getElementById('gymFields');
            const exerciseList = document.getElementById('exerciseList');
            const cancelButton = document.querySelector('.cancel-button');
            const addExerciseBtn = document.getElementById('addExercise');

            function createSetHTML(exerciseId, setNumber) {
                let weightValue = '';
                let repsValue = '';
                if (setNumber > 1) {
                    const lastSet = document.querySelector(`#exercise-${exerciseId} .exercise-set:last-child`);
                    if (lastSet) {
                        const inputs = lastSet.querySelectorAll('.input-with-label input');
                        if (inputs.length >= 2) {
                            weightValue = inputs[0].value || '';
                            repsValue = inputs[1].value || '';
                        }
                    }
                }
                return `
                    <div class="exercise-set">
                        <div class="input-with-label">
                            <label>Weight</label>
                            <input type="number" name="exercise_${exerciseId}_set_${setNumber}_weight" placeholder="kg" min="0" step="0.5" value="${weightValue}">
                        </div>
                        <div class="input-with-label">
                            <label>Reps</label>
                            <input type="number" name="exercise_${exerciseId}_set_${setNumber}_reps" min="1" value="${repsValue}">
                        </div>
                        <button type="button" class="remove-exercise" onclick="removeSet(this)">×</button>
                    </div>
                `;
            }

            function createExerciseHTML(exerciseId) {
                return `
                    <div class="exercise-item" id="exercise-${exerciseId}">
                        <div class="exercise-header">
                            <div class="input-with-label exercise-name-input">
                                <label>Exercise Name</label>
                                <input type="text" name="exercise_${exerciseId}_name" required>
                            </div>
                            <button type="button" class="remove-exercise" onclick="removeExercise(this)">×</button>
                        </div>
                        <div class="exercise-sets">
                            ${createSetHTML(exerciseId, 1)}
                        </div>
                        <button type="button" class="add-set-button" onclick="addSet(${exerciseId})">
                            <span>+</span>
                            <span>Add Another Set</span>
                        </button>
                    </div>
                `;
            }

            let exerciseCounter = 0;

            window.addSet = function(exerciseId) {
                const exerciseDiv = document.getElementById(`exercise-${exerciseId}`);
                const setsDiv = exerciseDiv.querySelector('.exercise-sets');
                const setNumber = setsDiv.children.length + 1;
                const setHTML = createSetHTML(exerciseId, setNumber);
                setsDiv.insertAdjacentHTML('beforeend', setHTML);
            };

            window.removeExercise = function(button) {
                button.closest('.exercise-item').remove();
                reindexExercises();
            };

            window.removeSet = function(button) {
                button.closest('.exercise-set').remove();
                // Reindex sets within the exercise
                const exerciseDiv = button.closest('.exercise-item');
                const exerciseId = exerciseDiv.id.split('-')[1];
                const sets = exerciseDiv.querySelectorAll('.exercise-set');
                sets.forEach((set, index) => {
                    const inputs = set.querySelectorAll('input');
                    inputs[0].name = `exercise_${exerciseId}_set_${index + 1}_weight`;
                    inputs[1].name = `exercise_${exerciseId}_set_${index + 1}_reps`;
                });
            };

            function reindexExercises() {
                const exerciseItems = exerciseList.querySelectorAll('.exercise-item');
                exerciseCounter = exerciseItems.length;
                exerciseItems.forEach((item, index) => {
                    item.id = `exercise-${index}`;
                    const nameInput = item.querySelector('input[name^="exercise_"]');
                    nameInput.name = `exercise_${index}_name`;
                    const sets = item.querySelectorAll('.exercise-set');
                    sets.forEach((set, setIndex) => {
                        const inputs = set.querySelectorAll('input');
                        inputs[0].name = `exercise_${index}_set_${setIndex + 1}_weight`;
                        inputs[1].name = `exercise_${index}_set_${setIndex + 1}_reps`;
                    });
                    const addSetButton = item.querySelector('.add-set-button');
                    addSetButton.setAttribute('onclick', `addSet(${index})`);
                });
            }

            addExerciseBtn.addEventListener('click', () => {
                exerciseList.insertAdjacentHTML('beforeend', createExerciseHTML(exerciseCounter));
                exerciseCounter++;
            });

            addButton.addEventListener('click', () => {
                workoutForm.showModal();
                exerciseCounter = 0;
                exerciseList.innerHTML = '';
            });

            cancelButton.addEventListener('click', () => {
                workoutForm.close();
            });

            workoutType.addEventListener('change', () => {
                if (workoutType.value === 'R') {
                    runFields.classList.remove('hidden');
                    gymFields.classList.add('hidden');
                } else if (workoutType.value === 'G') {
                    gymFields.classList.remove('hidden');
                    runFields.classList.add('hidden');
                } else {
                    runFields.classList.add('hidden');
                    gymFields.classList.add('hidden');
                }
            });

            workoutForm.addEventListener('submit', (e) => {
                console.log('Form submitted');
            });
        });
});