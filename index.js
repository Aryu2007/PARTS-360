function readVehicleModels() {
    if (window.PARTS360_MODELS) return window.PARTS360_MODELS;
    const data = document.getElementById("parts360-models");
    if (!data) return null;
    try {
        window.PARTS360_MODELS = JSON.parse(data.textContent);
        return window.PARTS360_MODELS;
    } catch (error) {
        return null;
    }
}

function populateModels() {
    const brandSelect = document.getElementById("brand");
    const models = readVehicleModels();
    if (!brandSelect || !models) return;
    const targetId = brandSelect.dataset.modelTarget || "model";
    const modelSelect = document.getElementById(targetId);
    if (!modelSelect) return;
    const currentModel = modelSelect.dataset.currentModel || modelSelect.value;
    const selectedBrand = brandSelect.value;
    modelSelect.innerHTML = '<option value="">' + (selectedBrand ? "All Models" : "Select Model") + "</option>";
    (models[selectedBrand] || []).forEach(function(model) {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = model;
        if (model === currentModel) option.selected = true;
        modelSelect.appendChild(option);
    });
}

document.addEventListener("DOMContentLoaded", function() {
    populateModels();
    const brandSelect = document.getElementById("brand");
    if (brandSelect) brandSelect.addEventListener("change", populateModels);

    document.querySelectorAll(".thumb").forEach(function(button) {
        button.addEventListener("click", function() {
            const mainImage = document.getElementById("mainProductImage");
            if (mainImage) mainImage.src = button.dataset.image;
        });
    });
});
