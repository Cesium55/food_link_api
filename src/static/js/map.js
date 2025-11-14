window.addEventListener('load', function () {
    async function initMap() {
        try {
            await ymaps3.ready;


            ymaps3.import.registerCdn('https://cdn.jsdelivr.net/npm/{package}', '@yandex/ymaps3-default-ui-theme@0.0');


            const { YMap, YMapDefaultSchemeLayer, YMapMarker, YMapDefaultFeaturesLayer, YMapControls } = ymaps3;

            const {YMapGeolocationControl} = await ymaps3.import('@yandex/ymaps3-default-ui-theme');

            const map = new YMap(
                document.getElementById('app'),
                {
                    location: {
                        center: [37.588144, 55.733842],
                        zoom: 10
                    }
                },
                [
                    new YMapDefaultSchemeLayer({}),
                    new YMapDefaultFeaturesLayer()
                ]
            );


            map.addChild(
                // Using YMapControls you can change the position of the control
                new YMapControls({ position: 'right' })
                    // Add the geolocation control to the map
                    .addChild(new YMapGeolocationControl({easing: 'ease-in-out', duration: 2000, zoom: 10}))
            );




            // Получаем данные маркеров из глобальной переменной
            const markersData = window.MAP_MARKERS_DATA || [];

            // Создаем маркеры в цикле
            markersData.forEach(markerData => {
                const markerContainer = document.createElement('div');
                markerContainer.style.cssText = 'position: relative; width: 0; height: 0;';

                const markerElement = document.createElement('div');
                markerElement.className = 'marker-class';

                const markerText = document.createElement('span');
                markerText.className = 'marker-text';
                markerText.innerText = markerData.label;
                markerElement.appendChild(markerText);

                markerContainer.appendChild(markerElement);

                // Добавляем обработчик клика на маркер
                markerElement.addEventListener('click', () => {
                    // Добавляем анимацию пульсации
                    markerElement.classList.add('pulse');

                    // Убираем класс анимации после завершения
                    setTimeout(() => {
                        markerElement.classList.remove('pulse');
                    }, 300);

                    window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'markerClick', shopPointId: markerData.id, gembos: true }))

                    console.log('Marker clicked:', {
                        coordinates: markerData.coordinates,
                        label: markerData.label
                    });

                });

                const marker = new YMapMarker(
                    {
                        coordinates: markerData.coordinates
                    },
                    markerContainer
                );

                map.addChild(marker);
            });
        } catch (error) {
            console.error('Ошибка инициализации карты:', error);
        }
    }

    initMap();
});

