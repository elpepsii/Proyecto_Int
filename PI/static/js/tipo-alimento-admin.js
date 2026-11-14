document.addEventListener('DOMContentLoaded', () => {
    const categoria = document.querySelector('#id_tipo_producto');
    const tipoAlimento = document.querySelector('#id_tipo_alimento');
    if (!categoria || !tipoAlimento) return;

    const fila = tipoAlimento.closest('.form-row');
    const actualizar = () => {
        const esAlimento = categoria.value === 'alimento';
        fila.hidden = !esAlimento;
        tipoAlimento.disabled = !esAlimento;
        tipoAlimento.required = esAlimento;
    };
    categoria.addEventListener('change', actualizar);
    actualizar();
});
