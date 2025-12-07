document.addEventListener("DOMContentLoaded", () => {
    
    /* --- 1. CLOCK & WEATHER (Unchanged) --- */
    // ... [Clock and Weather code from previous correction] ...
    function updateClock() {
        const now = new Date();
        document.getElementById('clockTime').innerText = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', hour12: false});
        document.getElementById('clockDate').innerText = now.toLocaleDateString([], {weekday: 'long', month: 'short', day: 'numeric'});
    }
    setInterval(updateClock, 1000);
    updateClock();

    fetch('https://api.open-meteo.com/v1/forecast?latitude=28.61&longitude=77.20&current_weather=true')
        .then(r => r.json())
        .then(d => {
            if (d.current_weather) { 
                document.getElementById('weatherTemp').innerHTML = Math.round(d.current_weather.temperature) + "&deg;";
                const code = d.current_weather.weathercode;
                let desc = "Clear";
                if (code > 2) desc = "Cloudy";
                if (code > 50) desc = "Rainy";
                if (code > 70) desc = "Stormy";
                document.getElementById('weatherDesc').innerText = desc;
            }
        });


    /* --- 2. SLIDESHOW ENGINE --- */
    const slides = document.querySelectorAll('.slide');
    const progressBar = document.getElementById('progressBar');
    const contentWrapper = document.querySelector('.content-wrapper'); // Grab content wrapper
    
    const prevButton = document.getElementById('prevSlide');
    const nextButton = document.getElementById('nextSlide');

    let currentIndex = 0;
    let slideTimer;
    let isPaused = false;

    function showSlide(index, restartTimer = true) {
        if (slides.length === 0) return;

        // Ensure index wraps correctly
        currentIndex = (index + slides.length) % slides.length; 

        // Cleanup previous slide
        slides.forEach(s => {
            s.classList.remove('active-slide');
            const vid = s.querySelector('video');
            if (vid) { vid.pause(); }
        });

        // Activate new slide
        const current = slides[currentIndex];
        current.classList.add('active-slide');
        
        // Handle Video
        const type = current.getAttribute('data-type');
        const vid = current.querySelector('video');
        if (type === 'video' && vid) {
            vid.muted = true;
            vid.play();
        }

        if (restartTimer && !isPaused) {
            startTimer();
        }
    }
    
    function startTimer() {
        clearTimeout(slideTimer);
        const current = slides[currentIndex];
        let duration = parseInt(current.getAttribute('data-duration')) || 5000;
        
        // Reset Progress Bar Animation
        progressBar.style.transition = 'none';
        progressBar.style.width = '0%';
        
        setTimeout(() => {
            progressBar.style.transition = `width ${duration}ms linear`;
            progressBar.style.width = '100%';
        }, 50);

        // Schedule Next Slide
        slideTimer = setTimeout(() => {
            nextSlide();
        }, duration);
    }
    
    function pauseSlideshow() {
        isPaused = true;
        clearTimeout(slideTimer);
        progressBar.style.transition = 'none';
        progressBar.style.width = progressBar.offsetWidth / progressBar.parentElement.offsetWidth * 100 + '%'; // Hold current progress
        console.log("Slideshow Paused.");
    }
    
    function resumeSlideshow() {
        if (isPaused) {
            isPaused = false;
            // Immediate jump to next slide is safest way to resume after hover pause
            nextSlide(); 
        }
    }


    function nextSlide() {
        showSlide(currentIndex + 1);
        // Check for server updates on loop
        if(currentIndex === 0) checkUpdates();
    }
    
    function prevSlide() {
        showSlide(currentIndex - 1);
    }
    
    // --- Manual Control Listeners ---
    if(prevButton) prevButton.addEventListener('click', prevSlide);
    if(nextButton) nextButton.addEventListener('click', nextSlide);
    
    // --- Hold and Read Feature ---
    slides.forEach(slide => {
        const wrapper = slide.querySelector('.content-wrapper');
        if (wrapper) {
            wrapper.addEventListener('mouseenter', pauseSlideshow);
            wrapper.addEventListener('mouseleave', resumeSlideshow);
        }
    });


    /* --- 3. AUTO-UPDATE CHECKER (Unchanged) --- */
    let lastTs = 0;
    function checkUpdates() {
        fetch('/api/check_update') 
            .then(r => r.json())
            .then(data => {
                if (lastTs === 0) lastTs = data.timestamp;
                else if (data.timestamp > lastTs) {
                    console.log("New content found. Reloading...");
                    location.reload();
                }
            })
            .catch(e => console.log("Update check failed:", e));
    }

    // Initialize
    fetch('/api/check_update').then(r=>r.json()).then(d => lastTs = d.timestamp);
    if (slides.length > 0) showSlide(0);
});