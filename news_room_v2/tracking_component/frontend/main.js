
// Streamlit Component Scripts
function sendMessageToStreamlitClient(type, data) {
    const outData = Object.assign({
        isStreamlitMessage: true,
        type: type,
    }, data);
    window.parent.postMessage(outData, "*");
}

function init() {
    sendMessageToStreamlitClient("streamlit:componentReady", { apiVersion: 1 });
}

function setFrameHeight(height) {
    sendMessageToStreamlitClient("streamlit:setFrameHeight", { height: height });
}

// Tracking Logic
let hoverStartTime = 0;
let currentHoverId = null;

function sendEvent(eventType, targetId, meta = {}) {
    const eventData = {
        timestamp: new Date().toISOString(),
        event: eventType,
        target_id: targetId,
        ...meta
    };
    // Send directly to Python
    sendMessageToStreamlitClient("streamlit:setComponentValue", { value: eventData });
}

function onHoverStart(targetId) {
    currentHoverId = targetId;
    hoverStartTime = Date.now();
    // Optional: Send hover start event if needed immediately
    // sendEvent("hover_start", targetId);
}

function onHoverEnd(targetId) {
    if (currentHoverId === targetId) {
        const duration = Date.now() - hoverStartTime;
        if (duration > 500) { // Only log if hovered > 500ms
            sendEvent("hover", targetId, { duration_ms: duration });
        }
        currentHoverId = null;
    }
}

function onClick(targetId, url) {
    sendEvent("click", targetId, { url: url });
    // Let default link behavior happen if it's an anchor, or handle navigation
}

// Rendering
function render(event) {
    const data = event.data;
    if (data.type !== "streamlit:render") return;

    const args = data.args; // Arguments passed from Python
    const articles = args.articles || [];
    const keywords = args.keywords || [];

    const container = document.getElementById("content");
    container.innerHTML = ""; // Clear previous content

    // Create Grid
    const grid = document.createElement("div");
    grid.className = "grid-container";

    articles.forEach((article, index) => {
        const card = document.createElement("div");
        card.className = "news-card";
        card.dataset.id = article.id;

        // Header
        const header = document.createElement("div");
        header.className = "card-header";

        const infoSpan = document.createElement("div");
        infoSpan.innerHTML = `<span>#${index + 1}</span> <span class="score">Score: ${article.score.toFixed(2)}</span>`;

        const deleteBtn = document.createElement("span");
        deleteBtn.className = "delete-btn";
        deleteBtn.textContent = "✕";
        deleteBtn.title = "삭제 (관심 없음)";
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            sendEvent("remove_request", article.id);
        };

        header.appendChild(infoSpan);
        header.appendChild(deleteBtn);
        card.appendChild(header);

        // Body
        const body = document.createElement("div");
        body.className = "card-body";
        const titleLink = document.createElement("a");
        titleLink.href = article.url || "#";
        titleLink.target = "_blank";
        titleLink.className = "card-title";
        titleLink.textContent = `[${article.media}] ${article.title}`;

        // Highlight keywords
        if (keywords.length > 0) {
            // Simple highlight logic could be added here
        }

        titleLink.onclick = () => onClick(article.id, article.url);

        body.appendChild(titleLink);

        if (article.summary) {
            const summary = document.createElement("p");
            summary.className = "card-summary";
            summary.textContent = article.summary.substring(0, 100) + "...";
            body.appendChild(summary);
        }

        card.appendChild(body);

        // Footer (Actions)
        const footer = document.createElement("div");
        footer.className = "card-footer";

        // Rating Button (Simplified to "Rate" which sends event to open modal in Python?)
        // Or implement simple rating stars here?
        // User asked for slider. Slider in Python is easier.
        // Let's keep actions in Python if possible, or trigger a "rate_request" event.
        const rateBtn = document.createElement("button");
        rateBtn.className = "action-btn";
        rateBtn.textContent = article.is_rated ? "Rated ✅" : "Rate ⭐";
        rateBtn.onclick = (e) => {
            e.stopPropagation(); // Prevent card click
            sendEvent("rate_request", article.id);
        };
        footer.appendChild(rateBtn);

        card.appendChild(footer);

        // Event Listeners
        card.onmouseenter = () => onHoverStart(article.id);
        card.onmouseleave = () => onHoverEnd(article.id);

        grid.appendChild(card);
    });

    container.appendChild(grid);

    // Resize frame
    // Use a small timeout to ensure rendering is done
    setTimeout(() => {
        setFrameHeight(container.scrollHeight + 20); // Add padding
    }, 50);
}

window.addEventListener("message", render);
window.addEventListener("load", init);
