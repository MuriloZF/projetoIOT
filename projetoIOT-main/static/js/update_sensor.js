function showUpdateForm(sensor) {
    const modal = document.getElementById("updateModal");
    const sensorField= document.getElementById("updateSensor");
    sensorField.value = sensor;
    modal.style.display = "block";
}

function closeModal() {
    document.getElementById("updateModal").style.display = "none";
    document.getElementById("field").value = "";
    document.getElementById("sensorField").style.display = "none";
    document.getElementById("valorField").style.display = "none";
}

function toggleInput() {
    const selectedField = document.getElementById("field").value;
    document.getElementById("sensorField").style.display = selectedField === "sensor" ? "block" : "none";
    document.getElementById("valorField").style.display = selectedField === "valor" ? "block" : "none";
}
window.onclick = function(event) {
    const modal = document.getElementById("updateModal");
    if (event.target === modal) {
        closeModal();
    }
}
