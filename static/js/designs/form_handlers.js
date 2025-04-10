// Handle dynamic formsets for materials and customization options
function updateFormsetIndex(formset, prefix) {
    const forms = formset.getElementsByClassName(`${prefix}-form`);
    const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    
    Array.from(forms).forEach((form, index) => {
        Array.from(form.getElementsByTagName('input')).forEach(input => {
            input.name = input.name.replace(new RegExp(`${prefix}-\\d+`), `${prefix}-${index}`);
            input.id = input.id.replace(new RegExp(`${prefix}-\\d+`), `${prefix}-${index}`);
        });
        Array.from(form.getElementsByTagName('select')).forEach(select => {
            select.name = select.name.replace(new RegExp(`${prefix}-\\d+`), `${prefix}-${index}`);
            select.id = select.id.replace(new RegExp(`${prefix}-\\d+`), `${prefix}-${index}`);
        });
        Array.from(form.getElementsByTagName('label')).forEach(label => {
            if (label.getAttribute('for')) {
                label.setAttribute('for', label.getAttribute('for').replace(new RegExp(`${prefix}-\\d+`), `${prefix}-${index}`));
            }
        });
    });
    
    totalForms.value = forms.length;
}

function addFormsetForm(prefix) {
    const formset = document.getElementById(`${prefix}-formset`);
    const emptyForm = document.getElementById(`${prefix}-empty-form`);
    if (emptyForm) {
        const newForm = emptyForm.cloneNode(true);
        newForm.classList.remove('d-none');
        newForm.removeAttribute('id');
        
        // Initialize select2 for new form's select elements
        Array.from(newForm.getElementsByTagName('select')).forEach(select => {
            if (select.classList.contains('select2')) {
                $(select).select2();
            }
        });
        
        formset.appendChild(newForm);
        updateFormsetIndex(formset, prefix);
    }
}

function deleteFormsetForm(prefix, button) {
    const formDiv = button.closest(`.${prefix}-form`);
    const deleteCheckbox = formDiv.querySelector('input[type="checkbox"][name$="-DELETE"]');
    
    if (deleteCheckbox) {
        deleteCheckbox.checked = true;
        formDiv.style.display = 'none';
    } else {
        formDiv.remove();
    }
    
    const formset = document.getElementById(`${prefix}-formset`);
    updateFormsetIndex(formset, prefix);
}

// Initialize Select2 for dynamic form elements
function initializeSelect2() {
    $('.select2').select2({
        theme: 'bootstrap4',
        width: '100%'
    });
}

// Initialize material requirement calculations
function initializeMaterialCalculations() {
    const forms = document.querySelectorAll('.material-form');
    forms.forEach(form => {
        const lengthInput = form.querySelector('input[name$="length"]');
        const widthInput = form.querySelector('input[name$="width"]');
        const quantityInput = form.querySelector('input[name$="quantity_required"]');
        
        if (lengthInput && widthInput && quantityInput) {
            const calculateArea = () => {
                const length = parseFloat(lengthInput.value) || 0;
                const width = parseFloat(widthInput.value) || 0;
                const area = length * width;
                quantityInput.value = area.toFixed(2);
            };
            
            lengthInput.addEventListener('input', calculateArea);
            widthInput.addEventListener('input', calculateArea);
        }
    });
}

// Document ready handler
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Select2
    initializeSelect2();
    
    // Initialize material calculations
    initializeMaterialCalculations();
    
    // Handle customization toggle
    const customizableCheckbox = document.getElementById('id_is_customizable');
    const optionsDiv = document.getElementById('customization-options');
    if (customizableCheckbox && optionsDiv) {
        customizableCheckbox.addEventListener('change', function() {
            optionsDiv.style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Add material button handler
    document.getElementById('add-material').addEventListener('click', () => {
        addFormsetForm('materials');
        initializeMaterialCalculations();
    });
    
    // Add option button handler
    document.getElementById('add-option').addEventListener('click', () => {
        addFormsetForm('options');
    });
    
    // Delete button handlers
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-material')) {
            deleteFormsetForm('materials', e.target);
        } else if (e.target.classList.contains('delete-option')) {
            deleteFormsetForm('options', e.target);
        }
    });
});