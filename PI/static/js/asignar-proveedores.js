const formulario = document.querySelector('#asignar-proveedores');
const selectores = [...formulario.querySelectorAll('select')];
const guardar = document.querySelector('#guardar-asignaciones');
const estado = document.querySelector('#cambios-asignaciones');

function cambioProveedor(selector) {
    return selector.value !== formulario.elements[`inicial_${selector.name}`].value;
}

function actualizarCambios() {
    let pendientes = 0;
    for (const selector of selectores) {
        const cambio = cambioProveedor(selector);
        selector.closest('tr').classList.toggle('asignacion-editada', cambio);
        pendientes += Number(cambio);
    }
    guardar.hidden = pendientes === 0;
    estado.textContent = pendientes === 0 ? '' : `${pendientes} ${pendientes === 1 ? 'cambio pendiente' : 'cambios pendientes'}`;
}

formulario.addEventListener('change', actualizarCambios);
formulario.addEventListener('formdata', ({ formData }) => {
    for (const selector of selectores) {
        formData.delete(`inicial_${selector.name}`);
        if (!cambioProveedor(selector)) {
            formData.delete(selector.name);
        }
    }
});
window.addEventListener('pageshow', actualizarCambios);
actualizarCambios();
