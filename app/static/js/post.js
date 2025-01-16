// app/static/js/post.js

/* =========================================
   0) 전역 변수 및 유틸
========================================= */
const userId = window.userId || ""; // 혹은 다른 방식으로 로그인 유저 ID 가져오기

function sanitize(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// 댓글 페이지 당 개수
const COMMENTS_PER_PAGE = 15;

// 게시글 무한스크롤
let skip = 10;  // 초기 로드된 게시글 수
const limit = 10;
let isLoading = false; // 무한 스크롤 상태

// 댓글 데이터를 저장할 객체 (postId -> [comments])
const commentsData = {};

/* ============================================================
   1) 게시글 작성 모달 (다중 이미지 드래그/슬라이더 + 본문 작성)
============================================================= */

// 모달 DOM 요소
const modal = document.getElementById("create-post-modal");
const openModalButton = document.getElementById("open-create-post-modal");
const closeModalButton = document.querySelector(".close-button");

// 이미지 드래그 영역 및 내부 요소
const imageDragArea = document.getElementById("image-drag-area");
const hiddenFileInput = document.getElementById("hidden-file-input");
const imagePreview = document.getElementById("image-preview");
const imageNavLeft = document.getElementById("image-nav-left");
const imageNavRight = document.getElementById("image-nav-right");
const createPostButton = document.getElementById("create-post-submit");

// 작성 폼의 텍스트, 공개 여부
const createPostContent = document.getElementById("create-post-content");
const isPublicCheckbox = document.getElementById("create-is-public");

// 여러 장 이미지를 담을 배열
let selectedImages = [];
// 현재 미리보기 중인 이미지 인덱스
let currentImageIndex = 0;

/* ================ 모달 열기/닫기 ================ */
if (openModalButton) {
    openModalButton.addEventListener("click", (e) => {
        e.preventDefault();
        console.log("게시글 작성 버튼 클릭됨");
        if (modal) {
            modal.style.display = "block";
        }
        resetCreatePostModal(); // 모달 열 때 초기화
    });
}

function closeModal() {
    if (modal) {
        modal.style.display = "none";
    }
}
window.closeModal = closeModal;

// 모달 영역 밖을 클릭하면 닫기
window.addEventListener("click", (event) => {
    if (event.target === modal) {
        closeModal();
    }
});

// 모달 열 때 초기화
function resetCreatePostModal() {
    selectedImages = [];
    currentImageIndex = 0;
    updateImagePreview();
    createPostContent.value = "";
    isPublicCheckbox.checked = true;
}

/* ================ 이미지 드래그 앤 드롭 / 클릭 ================ */
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// 드래그 이벤트 바인딩
["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    imageDragArea.addEventListener(eventName, preventDefaults, false);
});

imageDragArea.addEventListener("dragover", () => {
    imageDragArea.classList.add("drag-over");
});
imageDragArea.addEventListener("dragleave", () => {
    imageDragArea.classList.remove("drag-over");
});
imageDragArea.addEventListener("drop", handleDrop);
imageDragArea.addEventListener("click", (e) => {
    if (e.target === imageDragArea) {
        hiddenFileInput.click();
    }
});

hiddenFileInput.addEventListener("change", (e) => {
    handleFiles(e.target.files);
});

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    imageDragArea.classList.remove("drag-over");
    handleFiles(files);
}

function handleFiles(files) {
    [...files].forEach((file) => {
        if (file.type.startsWith("image/")) {
            selectedImages.push(file);
        }
    });
    currentImageIndex = 0;
    updateImagePreview();
}

function updateImagePreview() {
    if (selectedImages.length === 0) {
        imagePreview.innerHTML = `<p style="color: #aaa;">이미지를 드래그하거나 클릭하여 추가해주세요</p>`;
        imageNavLeft.style.display = "none";
        imageNavRight.style.display = "none";
        return;
    }

    const currentFile = selectedImages[currentImageIndex];
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.innerHTML = `<img src="${e.target.result}" alt="미리보기" />`;
    };
    reader.readAsDataURL(currentFile);

    if (selectedImages.length > 1) {
        imageNavLeft.style.display = "block";
        imageNavRight.style.display = "block";
    } else {
        imageNavLeft.style.display = "none";
        imageNavRight.style.display = "none";
    }
}

imageNavLeft.addEventListener("click", () => {
    if (selectedImages.length > 1) {
        currentImageIndex = (currentImageIndex - 1 + selectedImages.length) % selectedImages.length;
        updateImagePreview();
    }
});
imageNavRight.addEventListener("click", () => {
    if (selectedImages.length > 1) {
        currentImageIndex = (currentImageIndex + 1) % selectedImages.length;
        updateImagePreview();
    }
});

/* ================ 게시글 작성 버튼 (폼 전송) ================ */
if (createPostButton) {
    createPostButton.addEventListener("click", async () => {
        const contentValue = createPostContent.value.trim();
        const isPublic = isPublicCheckbox.checked;

        if (!contentValue && selectedImages.length === 0) {
            alert("본문 혹은 이미지를 입력하세요.");
            return;
        }

        const formData = new FormData();
        formData.append("content", contentValue);
        formData.append("is_public", isPublic);

        selectedImages.forEach((file) => {
            formData.append("images", file);
        });

        try {
            const response = await fetch(`/post/create`, {
                method: "POST",
                credentials: "include",
                body: formData,
            });
            if (!response.ok) {
                const errData = await response.json();
                alert(`게시글 작성 실패: ${errData.detail || response.statusText}`);
                return;
            }
            const data = await response.json();
            alert("게시글이 작성되었습니다.");
            closeModal();
            location.reload(); // 새로고침
        } catch (error) {
            console.error("게시글 작성 중 오류:", error);
        }
    });
}

/* ================ 3. 게시글 로드 (무한 스크롤) ================ */
async function fetchPosts() {
    try {
        const response = await fetch(`/post?limit=${limit}&skip=${skip}&format=json`, {
            method: "GET",
            credentials: "include",
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(`게시글 가져오기 실패: ${errorData.detail || response.statusText}`);
            return;
        }

        const data = await response.json();
        const posts = data.posts;
        const postContainer = document.getElementById("post-container");

        posts.forEach((post) => {
            // 댓글 데이터 정렬 후 저장 (최신순)
            commentsData[post.id] = post.comments.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            // 게시글 요소 생성
            const postElement = document.createElement("div");
            postElement.className = "post";
            postElement.id = `post-${post.id}`;

            // 이미지 슬라이더 HTML 생성
            let imageSliderHTML = "";
            if (post.image_urls.length > 0) {
                const imageUrlsJSON = JSON.stringify(post.image_urls);
                console.log(`post.id: ${post.id}, imageUrlsJSON: ${imageUrlsJSON}`); // 디버깅 로그
                imageSliderHTML = `
                <div class="post-image-slider"
                     id="post-image-slider-${post.id}"
                     data-image-urls='${imageUrlsJSON}'>
                  <!-- 이미지가 두 장 이상일 때만 좌우 버튼 표시 -->
                  ${post.image_urls.length > 1 ? `
                  <button class="slider-btn left" onclick="prevImage('${post.id}')">
                    <i class="fas fa-chevron-left"></i>
                  </button>
                  ` : ''}
                  <!-- 실제 이미지 표시 영역 -->
                  <div class="slider-image-wrapper" id="slider-image-wrapper-${post.id}">
                    <img src="${sanitize(post.image_urls[0])}" alt="게시글 이미지" class="slider-image"
                         id="current-image-${post.id}">
                  </div>
                  ${post.image_urls.length > 1 ? `
                  <button class="slider-btn right" onclick="nextImage('${post.id}')">
                    <i class="fas fa-chevron-right"></i>
                  </button>
                  ` : ''}
                </div>
                `;

                // 이미지 인덱스 초기화
                imageIndices[post.id] = 0;
            }

            // 게시글 HTML
            postElement.innerHTML = `
                <div class="post-header">
                  <img src="/static/images/profile.png" alt="프로필 이미지" class="profile-pic">
                  <div class="author-name">${sanitize(post.author_id)}</div>
                </div>
                ${imageSliderHTML}
                <!-- 게시글 내용 -->
                <div class="post-content">${sanitize(post.content)}</div>
                <!-- 게시글 액션 (좋아요) -->
                <div class="post-actions">
                  <div class="actions">
                    <button
                      id="like-button-${post.id}"
                      class="like-button ${post.likes.includes(userId) ? "liked" : ""}"
                      onclick="toggleLike('${post.id}')"
                    >
                      <i class="${post.likes.includes(userId) ? "fas" : "far"} fa-heart"></i>
                    </button>
                  </div>
                  <div class="likes-count">좋아요 ${post.likes.length}개</div>
                </div>

                <!-- 댓글 영역 -->
                <div class="post-comments">
                  <h4>댓글</h4>
                  <div id="comments-${post.id}" class="comments">
                    ${
                post.comments.length > 0
                    ? `
                                  ${post.comments.slice(0, 2).map(c => `
                                    <div class="comment">
                                      <strong>${sanitize(c.user_id)}:</strong> ${sanitize(c.content)}
                                    </div>
                                  `).join("")}
                                  ${post.comments.length > 2 ? `
                                    <button class="show-more-comments" onclick="showMoreComments('${post.id}')">
                                      댓글 더보기
                                    </button>
                                    <div class="paginated-comments" style="display: none;">
                                      <div class="comments-list"></div>
                                      <div class="pagination-controls">
                                        <button class="prev-button" onclick="changePage('${post.id}', -1)">이전</button>
                                        <div class="page-buttons"></div>
                                        <button class="next-button" onclick="changePage('${post.id}', 1)">다음</button>
                                      </div>
                                    </div>
                                  ` : ""}
                                `
                    : `<p class="no-comments">댓글이 없습니다.</p>`
            }
                  </div>
                  <div class="comment-input-container">
                    <input
                      type="text"
                      placeholder="댓글을 입력하세요"
                      class="comment-input"
                      id="comment-input-${post.id}"
                    />
                    <button onclick="addComment('${post.id}')">게시</button>
                  </div>
                </div>
            `;

            postContainer.appendChild(postElement);
        });

        skip += limit;
    } catch (error) {
        console.error("게시글 가져오기 중 오류:", error);
    }
}

window.fetchPosts = fetchPosts;

// 무한 스크롤 이벤트
window.addEventListener("scroll", () => {
    if (isLoading) return;
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
        isLoading = true;
        const postContainer = document.getElementById("post-container");
        const spinner = document.createElement("div");
        spinner.className = "loading-spinner";
        postContainer.appendChild(spinner);

        fetchPosts()
            .then(() => {
                spinner.remove();
                isLoading = false;
            })
            .catch((error) => {
                console.error("게시글 로드 중 오류:", error);
                spinner.remove();
                isLoading = false;
            });
    }
});

// 페이지 로드시 추가 게시글 로드
if (document.getElementById("post-container")) {
    fetchPosts();
}

// 기존 '더 보기' 버튼 숨기기
const loadMoreButton = document.getElementById("load-more");
if (loadMoreButton) {
    loadMoreButton.style.display = "none";
}

/* =========================================
   별도의 전체 댓글 렌더링 함수
========================================= */
function renderInitialComments(postId) {
    const commentsContainer = document.getElementById(`comments-${postId}`);
    if (!commentsContainer) return;

    const allComments = commentsData[postId] || [];

    // 댓글이 없을 경우
    if (allComments.length === 0) {
        commentsContainer.innerHTML = `<p class="no-comments">댓글이 없습니다.</p>`;
        return;
    }

    // 댓글이 2개 이하
    if (allComments.length <= 2) {
        commentsContainer.innerHTML = allComments
            .map(c => `
                <div class="comment">
                  <span class="comment-author">${sanitize(c.user_id)}</span>
                  <span class="comment-text">${sanitize(c.content)}</span>
                </div>
            `)
            .join("");
        return;
    }

    // 댓글이 3개 이상
    const firstTwo = allComments.slice(0, 2);
    const rest = allComments.slice(2);

    commentsContainer.innerHTML = `
        ${firstTwo
        .map(c => `
                <div class="comment">
                  <span class="comment-author">${sanitize(c.user_id)}</span>
                  <span class="comment-text">${sanitize(c.content)}</span>
                </div>
            `)
        .join("")
    }
        <button class="show-more-comments" onclick="showMoreComments('${postId}')">
            댓글 더 보기
        </button>
        <div class="paginated-comments" style="display: none;">
            <div class="comments-list">
                ${rest
        .map(c => `
                        <div class="comment">
                          <span class="comment-author">${sanitize(c.user_id)}</span>
                          <span class="comment-text">${sanitize(c.content)}</span>
                        </div>
                    `)
        .join("")
    }
            </div>
        </div>
    `;
}
window.renderInitialComments = renderInitialComments;

/* ================ 4. 좋아요 토글 ================ */
async function toggleLike(postId) {
    const likeButton = document.getElementById(`like-button-${postId}`);
    const likesCountElement = document.querySelector(`#post-${postId} .likes-count`);

    if (!likeButton || !likesCountElement) {
        console.error(`좋아요 버튼 또는 좋아요 수 요소를 찾을 수 없습니다: postId=${postId}`);
        return;
    }

    const isLiked = likeButton.classList.contains("liked");
    const originalLikesCount = parseInt(likesCountElement.innerText.match(/\d+/)[0], 10);

    // 옵티미스틱 UI 업데이트
    if (isLiked) {
        likeButton.classList.remove("liked");
        likeButton.innerHTML = `<i class="far fa-heart"></i>`;
        likesCountElement.innerText = `좋아요 ${originalLikesCount - 1}개`;
    } else {
        likeButton.classList.add("liked");
        likeButton.innerHTML = `<i class="fas fa-heart"></i>`;
        likesCountElement.innerText = `좋아요 ${originalLikesCount + 1}개`;
    }

    try {
        const response = await fetch(`/post/${postId}/like`, {
            method: "POST",
            credentials: "include",
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(`좋아요 토글 실패: ${errorData.detail || response.statusText}`);
            // UI 원상복구
            if (isLiked) {
                likeButton.classList.add("liked");
                likeButton.innerHTML = `<i class="fas fa-heart"></i>`;
                likesCountElement.innerText = `좋아요 ${originalLikesCount}개`;
            } else {
                likeButton.classList.remove("liked");
                likeButton.innerHTML = `<i class="far fa-heart"></i>`;
                likesCountElement.innerText = `좋아요 ${originalLikesCount}개`;
            }
            return;
        }

        const data = await response.json();
        console.log('Toggle like response:', data);
        likesCountElement.innerText = `좋아요 ${data.post.likes.length}개`;
    } catch (error) {
        console.error("좋아요 토글 중 오류:", error);
        alert("좋아요 토글 중 오류가 발생했습니다.");
        // UI 원상복구
        if (isLiked) {
            likeButton.classList.add("liked");
            likeButton.innerHTML = `<i class="fas fa-heart"></i>`;
            likesCountElement.innerText = `좋아요 ${originalLikesCount}개`;
        } else {
            likeButton.classList.remove("liked");
            likeButton.innerHTML = `<i class="far fa-heart"></i>`;
            likesCountElement.innerText = `좋아요 ${originalLikesCount}개`;
        }
    }
}
window.toggleLike = toggleLike;

/* ================ 5. 댓글 추가 ================ */
async function addComment(postId) {
    const commentInput = document.getElementById(`comment-input-${postId}`);
    const content = commentInput.value.trim();

    if (!content) {
        alert("댓글 내용을 입력해주세요.");
        return;
    }

    try {
        const response = await fetch(`/post/${postId}/comments`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({ content }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(`댓글 추가 실패: ${errorData.detail || response.statusText}`);
            return;
        }

        const data = await response.json();

        // 댓글 입력 필드 초기화
        commentInput.value = "";

        // DOM 업데이트: 새로운 댓글을 상단에 추가
        const commentsContainer = document.getElementById(`comments-${postId}`);
        const newCommentHtml = `
            <div class="comment">
                <span class="comment-author">${sanitize(data.user_id)}</span>
                <span class="comment-text">${sanitize(data.content)}</span>
                <span class="comment-timestamp">${new Date(data.timestamp).toLocaleString()}</span>
            </div>
        `;
        commentsContainer.insertAdjacentHTML("afterbegin", newCommentHtml);

        alert(data.message);

    } catch (error) {
        console.error("댓글 추가 중 오류:", error);
        alert("댓글 추가 중 오류가 발생했습니다.");
    }
}

// HTML 특수문자 이스케이프 처리
function sanitize(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
window.addComment = addComment;

/* ================ 6. 댓글 더보기 (페이징) ================ */
function showMoreComments(postId) {
    const commentsContainer = document.getElementById(`comments-${postId}`);
    if (!commentsContainer) return;

    const paginatedComments = commentsContainer.querySelector(".paginated-comments");
    if (paginatedComments) {
        paginatedComments.style.display = "block";
        // 초기 페이지 설정
        renderComments(postId, 1);
    }

    // "댓글 더보기" 버튼 숨기기
    const showMoreButton = commentsContainer.querySelector(".show-more-comments");
    if (showMoreButton) {
        showMoreButton.style.display = "none";
    }
}
window.showMoreComments = showMoreComments;

function renderComments(postId, page) {
    const commentsList = document.querySelector(`#comments-${postId} .paginated-comments .comments-list`);
    const pageButtonsContainer = document.querySelector(`#comments-${postId} .paginated-comments .pagination-controls .page-buttons`);

    const allComments = commentsData[postId] || [];
    const totalComments = allComments.length;
    const totalPages = Math.ceil(totalComments / COMMENTS_PER_PAGE);

    if (page < 1) page = 1;
    if (page > totalPages) page = totalPages;

    const start = (page - 1) * COMMENTS_PER_PAGE;
    const end = start + COMMENTS_PER_PAGE;
    const commentsToDisplay = allComments.slice(start, end);

    // 댓글 리스트 업데이트
    commentsList.innerHTML = commentsToDisplay
        .map(
            (comment) => `
      <div class="comment">
        <strong>${sanitize(comment.user_id)}:</strong> ${sanitize(comment.content)}
      </div>
    `
        )
        .join("");

    // 페이지 번호 버튼 업데이트
    pageButtonsContainer.innerHTML = "";
    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement("button");
        pageButton.innerText = i;
        if (i === page) {
            pageButton.classList.add("active");
        }
        pageButton.onclick = () => renderComments(postId, i);
        pageButtonsContainer.appendChild(pageButton);
    }

    const prevButton = document.querySelector(`#comments-${postId} .paginated-comments .pagination-controls .prev-button`);
    const nextButton = document.querySelector(`#comments-${postId} .paginated-comments .pagination-controls .next-button`);

    if (page === 1) {
        prevButton.disabled = true;
        prevButton.style.opacity = 0.5;
        prevButton.style.cursor = "not-allowed";
    } else {
        prevButton.disabled = false;
        prevButton.style.opacity = 1;
        prevButton.style.cursor = "pointer";
    }

    if (page === totalPages) {
        nextButton.disabled = true;
        nextButton.style.opacity = 0.5;
        nextButton.style.cursor = "not-allowed";
    } else {
        nextButton.disabled = false;
        nextButton.style.opacity = 1;
        nextButton.style.cursor = "pointer";
    }
}

function changePage(postId, direction) {
    const commentsContainer = document.getElementById(`comments-${postId}`);
    const paginatedComments = commentsContainer.querySelector(".paginated-comments");
    if (!paginatedComments) return;

    const currentPageButton = paginatedComments.querySelector(".pagination-controls .page-buttons .active");
    if (!currentPageButton) return;

    let currentPage = parseInt(currentPageButton.innerText, 10);

    const allComments = commentsData[postId] || [];
    const totalPages = Math.ceil(allComments.length / COMMENTS_PER_PAGE);

    let newPage = currentPage + direction;
    if (newPage < 1) newPage = 1;
    if (newPage > totalPages) newPage = totalPages;

    renderComments(postId, newPage);
}
window.changePage = changePage;

/* ================ 7. 게시글 수정, 삭제 예시 ================ */
async function openEditModal(postId) {
    // 예: 모달 열기 등
    console.log("게시글 수정 모달 열기:", postId);
    // 필요한 로직 추가
}
window.openEditModal = openEditModal;

async function deletePost(postId) {
    if (!confirm("정말 이 게시글을 삭제하시겠습니까?")) return;
    try {
        const response = await fetch(`/post/${postId}`, {
            method: "DELETE",
            credentials: "include",
        });

        if (!response.ok) {
            const errorData = await response.json();
            alert(`게시글 삭제 실패: ${errorData.detail || response.statusText}`);
            return;
        }

        const data = await response.json();
        alert("게시글이 삭제되었습니다.");
        // DOM에서 게시글 제거
        const postElement = document.getElementById(`post-${postId}`);
        if (postElement) {
            postElement.remove();
        }
    } catch (error) {
        console.error("게시글 삭제 중 오류:", error);
    }
}
window.deletePost = deletePost;


window.nextImage = nextImage;
window.prevImage = prevImage;

const imageIndices = {}; // 각 게시글의 현재 이미지 인덱스 저장

function prevImage(postId) {
    console.log(`prevImage called for postId: ${postId}`);
    const sliderWrapper = document.getElementById(`slider-image-wrapper-${postId}`);
    const currentImage = document.getElementById(`current-image-${postId}`);
    const rawImages = sliderWrapper.parentNode.dataset.imageUrls; // JSON 문자열 가져오기

    console.log(`post.id: ${postId}, rawImages: ${rawImages}`); // 디버깅 로그

    if (!rawImages || rawImages.trim() === "") {
        console.error("이미지 데이터가 비어 있습니다.");
        return;
    }

    let images;
    try {
        images = JSON.parse(rawImages); // JSON 문자열 파싱
    } catch (error) {
        console.error("JSON 파싱 오류:", error, "원본 데이터:", rawImages);
        return;
    }

    if (!images || images.length === 0) {
        console.error("이미지 배열이 유효하지 않습니다.");
        return;
    }

    if (!imageIndices[postId]) imageIndices[postId] = 0; // 기본 인덱스 설정
    imageIndices[postId] = (imageIndices[postId] - 1 + images.length) % images.length; // 이전 인덱스 계산

    currentImage.src = images[imageIndices[postId]]; // 이전 이미지로 변경
}

function nextImage(postId) {
    const sliderWrapper = document.getElementById(`slider-image-wrapper-${postId}`);
    const currentImage = document.getElementById(`current-image-${postId}`);
    const rawImages = sliderWrapper.parentNode.dataset.imageUrls; // JSON 문자열 가져오기

    console.log(`post.id: ${postId}, rawImages: ${rawImages}`); // 디버깅 로그

    if (!rawImages || rawImages.trim() === "") {
        console.error("이미지 데이터가 비어 있습니다. postId:", postId);
        return;
    }

    let images;
    try {
        images = JSON.parse(rawImages); // JSON 문자열 파싱
    } catch (error) {
        console.error("JSON 파싱 오류:", error, "원본 데이터:", rawImages);
        return;
    }

    if (!images || images.length === 0) {
        console.warn("이미지 배열이 비어 있습니다. postId:", postId);
        return;
    }

    if (!imageIndices[postId]) imageIndices[postId] = 0; // 기본 인덱스 설정
    imageIndices[postId] = (imageIndices[postId] + 1) % images.length; // 다음 인덱스 계산

    currentImage.src = images[imageIndices[postId]]; // 다음 이미지로 변경
}