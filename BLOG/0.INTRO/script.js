document.addEventListener('DOMContentLoaded', () => {
    // Add smooth scroll behavior for cards
    const cards = document.querySelectorAll('.card');
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        observer.observe(card);
    });

    // Follow button interaction
    const followBtn = document.querySelector('.follow-btn');
    followBtn.addEventListener('click', () => {
        followBtn.textContent = '팔로우됨!';
        followBtn.style.backgroundColor = '#4CAF50';
        followBtn.disabled = true;
    });

    // Add hover effect for stack items
    const stackItems = document.querySelectorAll('.stack-category li');
    stackItems.forEach(item => {
        item.addEventListener('mouseenter', () => {
            item.style.color = '#2196F3';
            item.style.paddingLeft = '10px';
        });

        item.addEventListener('mouseleave', () => {
            item.style.color = '';
            item.style.paddingLeft = '';
        });
    });
}); 