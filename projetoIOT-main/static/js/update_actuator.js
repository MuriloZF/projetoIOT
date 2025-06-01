function showUpdateForm(actuador) {
    const modal = document.getElementById("updateModal");
    const actuatorField= document.getElementById("updateActuator");
    actuatorField.value = actuador;
    modal.style.display = "block";
}

function closeModal() {
    document.getElementById("updateModal").style.display = "none";
    document.getElementById("field").value = "";
    document.getElementById("actuatorField").style.display = "none";
    document.getElementById("valorField").style.display = "none";
}

function toggleInput() {
    const selectedField = document.getElementById("field").value;
    document.getElementById("actuatorField").style.display = selectedField === "actuator" ? "block" : "none";
    document.getElementById("valorField").style.display = selectedField === "valor" ? "block" : "none";
}
window.onclick = function(event) {
    const modal = document.getElementById("updateModal");
    if (event.target === modal) {
        closeModal();
    }
}