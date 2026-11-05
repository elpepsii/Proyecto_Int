/* carrusel.js — Carrusel del home (vanilla JS, sin librerías).
   Controla la clase .activa sobre los slides y los puntos; rota solo
   cada 5 segundos y se detiene mientras el mouse está encima. */
(function () {
    'use strict';

    var carrusel = document.querySelector('.carrusel');
    if (!carrusel) return;   // la página no tiene carrusel: no hace nada

    var slides = carrusel.querySelectorAll('.carrusel-slide');
    var puntos = carrusel.querySelectorAll('.punto');
    var actual = 0;
    var temporizador = null;

    function mostrar(indice) {
        // índice circular: del último slide vuelve al primero
        actual = (indice + slides.length) % slides.length;
        slides.forEach(function (s, i) {
            s.classList.toggle('activa', i === actual);
        });
        puntos.forEach(function (p, i) {
            p.classList.toggle('activa', i === actual);
        });
    }

    function automatico() {
        clearInterval(temporizador);
        temporizador = setInterval(function () { mostrar(actual + 1); }, 5000);
    }

    carrusel.querySelector('.carrusel-ant').addEventListener('click', function () {
        mostrar(actual - 1);
        automatico();          // reinicia la cuenta para no saltar rápido
    });
    carrusel.querySelector('.carrusel-sig').addEventListener('click', function () {
        mostrar(actual + 1);
        automatico();
    });
    puntos.forEach(function (p, i) {
        p.addEventListener('click', function () {
            mostrar(i);
            automatico();
        });
    });

    // pausa cuando el usuario está mirando un banner
    carrusel.addEventListener('mouseenter', function () { clearInterval(temporizador); });
    carrusel.addEventListener('mouseleave', automatico);

    mostrar(0);
    automatico();
})();
