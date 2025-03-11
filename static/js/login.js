document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");

    // Show login form by default
    loginForm.style.display = "flex";

    window.showLogin = function () {
        loginForm.style.display = "flex";
        signupForm.style.display = "none";
    };

    window.showSignup = function () {
        loginForm.style.display = "none";
        signupForm.style.display = "flex";
    };
});
