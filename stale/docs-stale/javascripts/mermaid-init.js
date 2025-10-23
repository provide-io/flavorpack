document.addEventListener('DOMContentLoaded', function() {
    // Initialize mermaid when the page loads
    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
        
        // Find all mermaid code blocks and convert them
        document.querySelectorAll('pre code.language-mermaid').forEach(function(element) {
            const graphDefinition = element.textContent;
            const graphDiv = document.createElement('div');
            graphDiv.className = 'mermaid';
            graphDiv.textContent = graphDefinition;
            element.parentNode.parentNode.replaceChild(graphDiv, element.parentNode);
        });
        
        // Re-render any mermaid diagrams
        mermaid.init();
    }
});