export class LanguageCarousel {
    constructor() {
        this.slides = document.querySelectorAll('.carousel-text');
        this.currentSlide = 0;
        this.slideInterval = 2250;
        
        // Initialize the first slide
        this.slides[0].classList.add('active');
    }

    nextSlide() {
        this.slides[this.currentSlide].classList.remove('active');
        this.slides[this.currentSlide].classList.add('inactive');

        this.currentSlide = (this.currentSlide + 1) % this.slides.length;

        setTimeout(() => {
            this.slides.forEach(slide => slide.classList.remove('inactive'));
            this.slides[this.currentSlide].classList.add('active');
        }, 500);
    }

    start() {
        setInterval(() => this.nextSlide(), this.slideInterval);
    }
}