document.addEventListener("DOMContentLoaded", () => {
    AOS.init({
        duration: 1200,
        once: true,
    });

    const studentIdField = document.getElementById('studentId');
    const studentPasswordField = document.getElementById('studentPasswordField');
    const adminUsernameField = document.getElementById('adminUsername');
    const adminPasswordField = document.getElementById('adminPasswordField');
    const validationMessageContainer = document.getElementById("validationMessageContainer");

    const studentIdRegex = /^AAIS\/0559\/\d{3}$/;

    function validateInput(input, regex, messageElementId, type) {
        const value = input.value.trim();
        const messageElement = document.getElementById(messageElementId);
        if (value) {
            if (regex.test(value)) {
                messageElement.textContent = "✔️ Valid " + type + " format.";
                messageElement.className = "validation-message text-success";
                input.classList.add('valid');
                input.classList.remove('invalid');
            } else {
                messageElement.textContent = "❌ Invalid " + type + " format. Use " + (type === "Student ID" ? "AAIS/0559/XXX" : "a valid username") + ".";
                messageElement.className = "validation-message text-danger";
                input.classList.add('invalid');
                input.classList.remove('valid');
            }
        } else {
            messageElement.textContent = "";
            input.classList.remove('valid', 'invalid');
        }
    }

    studentIdField.addEventListener("input", () => validateInput(studentIdField, studentIdRegex, 'studentIdValidation', 'Student ID'));
    adminUsernameField.addEventListener("input", () => validateInput(adminUsernameField, /.+/, 'adminUsernameValidation', 'Username'));

    [studentPasswordField, adminPasswordField].forEach(passwordField => {
        passwordField.addEventListener("input", () => {
            const isStudent = passwordField.id === 'studentPasswordField';
            const messageElement = document.getElementById(isStudent ? 'studentPasswordValidation' : 'adminPasswordValidation');
            const value = passwordField.value.trim();
            if (value) {
                messageElement.textContent = "✔️ Password entered.";
                messageElement.className = "validation-message text-success";
                passwordField.classList.add('valid');
                passwordField.classList.remove('invalid');
            } else {
                messageElement.textContent = "❌ Password cannot be empty.";
                messageElement.className = "validation-message text-danger";
                passwordField.classList.add('invalid');
                passwordField.classList.remove('valid');
            }
        });
    });

    // Toggle between forms
    function toggleForm(type) {
        const studentForm = document.getElementById('studentLoginForm');
        const adminForm = document.getElementById('adminLoginForm');
        const studentBtn = document.getElementById('studentLoginBtn');
        const adminBtn = document.getElementById('adminLoginBtn');

        if (type === 'student') {
            studentForm.classList.add('active');
            adminForm.classList.remove('active');
            studentBtn.classList.add('active');
            adminBtn.classList.remove('active');
        } else {
            adminForm.classList.add('active');
            studentForm.classList.remove('active');
            adminBtn.classList.add('active');
            studentBtn.classList.remove('active');
        }

        clearFieldsAndMessages();

        // Reset reCAPTCHA for the newly visible form
        if (typeof grecaptcha !== 'undefined') {
            grecaptcha.reset();
        }
    }

    document.getElementById('studentLoginBtn').addEventListener('click', () => toggleForm('student'));
    document.getElementById('adminLoginBtn').addEventListener('click', () => toggleForm('admin'));

    function clearFieldsAndMessages() {
        [studentIdField, studentPasswordField, adminUsernameField, adminPasswordField].forEach(field => {
            field.value = '';
            field.classList.remove('valid', 'invalid');
        });
        ['studentIdValidation', 'studentPasswordValidation', 'adminUsernameValidation', 'adminPasswordValidation'].forEach(id => {
            document.getElementById(id).textContent = '';
        });
        validationMessageContainer.innerHTML = '';
    }

    function togglePasswordVisibility(targetId) {
        const passwordField = document.getElementById(targetId);
        const toggleIcon = passwordField.nextElementSibling.querySelector('i');
        if (passwordField.type === 'password') {
            passwordField.type = 'text';
            toggleIcon.classList.replace('fa-eye', 'fa-eye-slash');
        } else {
            passwordField.type = 'password';
            toggleIcon.classList.replace('fa-eye-slash', 'fa-eye');
        }
        toggleIcon.parentElement.classList.add('animate__animated', 'animate__flipInX');
        setTimeout(() => toggleIcon.parentElement.classList.remove('animate__animated', 'animate__flipInX'), 1000);
    }

    document.querySelectorAll('.toggle-icon').forEach(icon => {
        icon.addEventListener('click', () => togglePasswordVisibility(icon.getAttribute('data-target')));
    });

    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', event => {
            const button = form.querySelector('button[type="submit"]');
            button.disabled = true;
            button.querySelector('.spinner-border').style.display = 'inline-block';
            button.classList.add('animate__animated', 'animate__pulse');
        });
    });

    document.querySelectorAll('.toggle-btn, .btn-primary').forEach(btn => {
        btn.addEventListener('mouseenter', () => btn.classList.add('animate__animated', 'animate__rubberBand'));
        btn.addEventListener('mouseleave', () => btn.classList.remove('animate__rubberBand'));
    });
});