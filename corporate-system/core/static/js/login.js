const container = document.getElementById('blob-container');

// Get colors from CSS Variables
const style = getComputedStyle(document.documentElement);
const colors = [
    style.getPropertyValue('--blob-1'),
    style.getPropertyValue('--blob-2'),
    style.getPropertyValue('--blob-3'),
    style.getPropertyValue('--blob-4')
];

class Blob {
    constructor(color) {
        this.element = document.createElement('div');
        this.element.className = 'blob';
        
        const size = Math.random() * 300 + 300;
        this.element.style.width = `${size}px`;
        this.element.style.height = `${size}px`;
        this.element.style.backgroundColor = color;
        
        this.x = Math.random() * window.innerWidth;
        this.y = Math.random() * window.innerHeight;
        this.dx = (Math.random() - 0.5) * 1.5; // Slower, smoother movement
        this.dy = (Math.random() - 0.5) * 1.5;
        
        container.appendChild(this.element);
    }

    animate() {
        this.x += this.dx;
        this.y += this.dy;

        if (this.x < -100 || this.x > window.innerWidth) this.dx *= -1;
        if (this.y < -100 || this.y > window.innerHeight) this.dy *= -1;

        this.element.style.transform = `translate(${this.x}px, ${this.y}px)`;
        requestAnimationFrame(() => this.animate());
    }
}

colors.forEach(color => new Blob(color).animate());