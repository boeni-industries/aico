document.addEventListener('DOMContentLoaded', function() {
  // Find the header logo link
  const logoLink = document.querySelector('.md-header__button.md-logo');
  
  if (logoLink) {
    // Update the logo link to point to welcome.md instead of index.html
    logoLink.setAttribute('href', window.location.pathname.split('/').slice(0, -1).join('/') + '/welcome/');
  }
});
