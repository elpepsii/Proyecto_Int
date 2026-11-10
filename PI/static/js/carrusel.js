(function () {
    const carrusel = document.querySelector('.carrusel');
    if (!carrusel) return;

    const slides = carrusel.querySelectorAll('.carrusel-slide');
    const puntos = carrusel.querySelectorAll('.punto');
    const pausa = carrusel.querySelector('.carrusel-pausa');
    let actual = 0;
    let temporizador;

    function mostrar(indice) {
        actual = (indice + slides.length) % slides.length;
        slides.forEach((slide, i) => {
            slide.classList.toggle('activa', i === actual);
            slide.setAttribute('aria-hidden', String(i !== actual));
        });
        puntos.forEach((punto, i) => {
            punto.classList.toggle('activa', i === actual);
            if (i === actual) punto.setAttribute('aria-current', 'true');
            else punto.removeAttribute('aria-current');
        });
    }

    function reiniciar() {
        clearInterval(temporizador);
        if (pausa.getAttribute('aria-pressed') === 'false') {
            temporizador = setInterval(() => {
                if (!carrusel.matches(':hover, :focus-within')) mostrar(actual + 1);
            }, 5000);
        }
    }

    function irA(indice) {
        mostrar(indice);
        reiniciar();
    }

    function ajustarPausa(pausado) {
        pausa.setAttribute('aria-pressed', String(pausado));
        pausa.textContent = pausado ? '▶' : 'Ⅱ';
        reiniciar();
    }

    carrusel.querySelector('.carrusel-ant').addEventListener('click', () => irA(actual - 1));
    carrusel.querySelector('.carrusel-sig').addEventListener('click', () => irA(actual + 1));
    puntos.forEach((punto, i) => punto.addEventListener('click', () => irA(i)));
    pausa.addEventListener('click', () => ajustarPausa(pausa.getAttribute('aria-pressed') === 'false'));

    const movimientoReducido = window.matchMedia('(prefers-reduced-motion: reduce)');
    movimientoReducido.addEventListener('change', evento => ajustarPausa(evento.matches));
    ajustarPausa(movimientoReducido.matches);
    carrusel.querySelectorAll('.carrusel-flechas, .carrusel-controles').forEach(grupo => {
        grupo.hidden = false;
    });
})();
