function showUpdateForm(user) {
    const modal = document.getElementById("updateModal");
    const userField = document.getElementById("updateUser");
    userField.value = user;
    modal.style.display = "block";
}

function closeModal() {
    document.getElementById("updateModal").style.display = "none";
    document.getElementById("field").value = "";
    document.getElementById("nomeField").style.display = "none";
    document.getElementById("senhaField").style.display = "none";
}

function toggleInput() {
    const selectedField = document.getElementById("field").value;
    document.getElementById("nomeField").style.display = selectedField === "user" ? "block" : "none";
    document.getElementById("senhaField").style.display = selectedField === "password" ? "block" : "none";
}
window.onclick = function(event) {
    const modal = document.getElementById("updateModal");
    if (event.target === modal) {
        closeModal();
    }
}
