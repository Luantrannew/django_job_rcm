import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def process_cv_to_jobs(cv_data, job_data):
    """
    Tìm kiếm các công việc phù hợp với CV dựa trên phân tích văn bản.
    :param cv_data: Dữ liệu CV gồm kỹ năng, kinh nghiệm, dự án.
    :param job_data: Danh sách công việc từ database.
    :return: DataFrame chứa danh sách công việc phù hợp.
    """
    # Chuyển đổi dữ liệu CV thành văn bản
    cv_text = " ".join(cv_data["skills"] + cv_data["experiences"] + cv_data["projects"])

    # Chuyển đổi danh sách công việc thành văn bản mô tả công việc
    job_texts = [f"{job['job_name']} {job['industry']} {job['jd']}" for job in job_data]

    # Sử dụng TF-IDF để vector hóa văn bản
    vectorizer = TfidfVectorizer(stop_words='english')
    all_texts = [cv_text] + job_texts  # Gộp CV và các công việc
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Tính toán độ tương đồng cosine giữa CV và các công việc
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    # Gán điểm tương đồng vào danh sách công việc
    job_scores = pd.DataFrame(job_data)
    job_scores["similarity"] = cosine_similarities

    # Sắp xếp công việc theo mức độ phù hợp giảm dần
    job_scores = job_scores.sort_values(by="similarity", ascending=False).head(30)

    return job_scores
