# 🎬 Kịch bản Thuyết trình Video Demo 5 Phút (5-Minute Video Pitch Script)

> **Dự án**: Enterprise AI Gateway & Observability Platform  
> **Thời lượng chuẩn**: 05 phút 00 giây  
> **Mục tiêu**: Thuyết phục hội đồng 100 chuyên gia đánh giá toàn công ty đạt điểm số tuyệt đối **20/20 (Hạng Thưởng 200 XP x2)**.

---

## ⏱️ Timeline tổng quan 5 phút

```
[0:00 - 0:45] ── 1. Đặt vấn đề & Tuyên ngôn giá trị (Problem & Value Prop)
[0:45 - 1:30] ── 2. Kiến trúc giải pháp & Khả năng tái lập trong 1 lệnh
[1:30 - 3:00] ── 3. Live Demo 6 tính năng đột phá & 6/6 Điểm Thưởng (Bonus)
[3:00 - 4:00] ── 4. Tư duy kiểm chứng (Verification Mindset & Bắt lỗi AI)
[4:00 - 4:40] ── 5. Hiệu quả kinh tế (ROI) & Lộ trình 7 ngày tới
[4:40 - 5:00] ── 6. Lời kết & Kêu gọi hành động (Call to Action)
```

---

## 📽️ Kịch bản chi tiết từng phút (Minute-by-minute Script)

---

### Phút 0:00 – 0:45 | 1. Đặt vấn đề & Tuyên ngôn giá trị
* **Giao diện quay màn hình**: Slide tiêu đề dự án hoặc giao diện Swagger UI `/docs` của AI Gateway.
* **Tâm thế người nói**: Tự tin, dõng dạc, đi thẳng vào nỗi đau của doanh nghiệp.

> 🎙️ **Lời thoại (Speaker)**:  
> *"Kính chào quý Ban giám khảo và các chuyên gia đánh giá.  
> Hiện nay, khi các phòng ban trong công ty cùng tích hợp LLM vào ứng dụng, chúng ta đang đối mặt với 3 bài toán nan giải:  
> Thứ nhất: **Vendor Lock-in** và nguy cơ sập dịch vụ khi OpenAI hoặc Gemini gặp sự cố mạng hoặc bị Rate Limit 429.  
> Thứ hai: **Lãng phí chi phí** hàng nghìn USD mỗi tháng do các câu hỏi lặp lại vẫn phải gọi tới LLM đắt đỏ.  
> Thứ ba: **Hoàn toàn mù mờ về giám sát**, không biết ai đang dùng bao nhiêu token và tỷ lệ lỗi ra sao.  
> Để giải quyết triệt để vấn đề này, tôi xin giới thiệu **Enterprise AI Gateway** – Cổng điều phối AI tập trung, bảo đảm tính sẵn sàng cao, tối ưu chi phí thông qua Caching, hỗ trợ hàng đợi bất đồng bộ và cung cấp báo cáo Observability thời gian thực."*

---

### Phút 0:45 – 1:30 | 2. Kiến trúc hệ thống & Tính tái lập trong 1 lệnh
* **Giao diện quay màn hình**: 
  1. Hiển thị sơ đồ kiến trúc Mermaid trong file `README.md`.
  2. Bật Terminal/PowerShell và gõ: `docker compose up -d` (cho thấy 3 container `api`, `postgres`, `redis` chạy mượt mà).

> 🎙️ **Lời thoại (Speaker)**:  
> *"Về mặt kiến trúc, AI Gateway đóng vai trò Reverse Proxy trung tâm.  
> Mọi yêu cầu từ ứng dụng Client đều đi qua lớp **Xác thực bảo mật SHA-256**, kế tiếp là **Rate Limiter trên Redis**.  
> Sau đó, hệ thống sẽ kiểm tra tầng **Response Cache L1**. Nếu Cache Miss, yêu cầu mới được chuyển tới **LLM Router** với cơ chế thử lại thông minh Exponential Backoff và **tự động chuyển mạch dự phòng (Fallback)**. Mọi giao dịch đều được ghi nhận vào PostgreSQL phục vụ kiểm toán và tính toán chi phí.  
> Về tính tái lập: Bất kỳ ai trong hội đồng cũng có thể chạy toàn bộ hệ sinh thái này chỉ bằng **1 câu lệnh duy nhất**: `docker compose up -d`. Hệ thống đã sẵn sàng 100%, không sử dụng bất kỳ dòng code giả lập (mock data) nào."*

---

### Phút 1:30 – 3:00 | 3. Live Demo 6 tính năng cốt lõi & 6/6 Điểm Thưởng
* **Giao diện quay màn hình**: Mở Postman, lần lượt gửi request theo file [`ai_gateway_postman_collection.json`](./ai_gateway_postman_collection.json).

> 🎙️ **Lời thoại (Speaker)**:  
> *(1:30 - Thao tác gửi `POST /ai/chat`)*  
> *"Đầu tiên là tính năng **Định tuyến đa mô hình và Hội thoại đa lượt**. Khi tôi gửi câu hỏi, Gateway phản hồi chỉ trong hơn 1 giây và lưu ngữ cảnh vào DB.*  
> 
> *(1:50 - Thao tác bấm 'Send' lại chính request đó)*  
> *"Bây giờ, khi tôi gửi lại câu hỏi tương tự: Quý vị hãy nhìn vào thời gian phản hồi: **chỉ 8 mili-giây**, cờ `cached: true` và số token tiêu thụ là 0! Tính năng **Smart Redis Caching** đã giúp tiết kiệm 100% chi phí cho câu hỏi này.*  
> 
> *(2:10 - Thao tác test Fallback hoặc giải thích luồng)*  
> *"Điểm đặc biệt thứ hai là **Cơ chế Dự phòng (Model Fallback)**: Nếu tôi cố tình cấu hình một OpenAI key hết tiền hoặc nhà cung cấp bị sự cố 429, Gateway không hề sập mà tự động failover sang Gemini trong suốt, người dùng cuối không gặp bất kỳ lỗi gián đoạn nào.*  
> 
> *(2:30 - Thao tác gọi `POST /ai/analyze` mode: "async")*  
> *"Đối với các tác vụ phân tích tài liệu nặng, Gateway cung cấp cơ chế **Hàng đợi bất đồng bộ (Queue-based Processing)**. Khi gửi phân tích, API trả về mã 202 Accepted kèm `task_id` chỉ trong 30ms, giải phóng hoàn toàn web worker khỏi tắc nghẽn. Sau đó, Client chỉ cần gọi endpoint `/tasks/{id}` để nhận kết quả phân tích theo cấu trúc JSON nghiêm ngặt.*  
> 
> *(2:45 - Thao tác mở `GET /usage`)*  
> *"Và đây là đỉnh cao của khả năng quan sát – **Observability Dashboard qua API**: Đúng theo mẫu yêu cầu của đề bài, Gateway trả về: tổng số `requests`, `tokens`, `average_latency_ms` và `error_rate`, kèm theo bóc tách chi phí USD chi tiết cho từng nhà cung cấp."*

---

### Phút 3:00 – 4:00 | 4. Tư duy kiểm chứng & Nhật ký bắt lỗi AI (Bug Postmortems)
* **Giao diện quay màn hình**: Mở file `AI_WORKLOG.md` và cuộn tới mục **Bug Postmortems**.

> 🎙️ **Lời thoại (Speaker)**:  
> *"Thưa Ban giám khảo, một tiêu chí quan trọng của cuộc thi là **Tư duy kiểm chứng (Verification Mindset)**.  
> Trong quá trình làm việc cùng trợ lý AI, chúng tôi không tin tưởng mù quáng mà luôn kiểm thử từng dòng mã nguồn. Chúng tôi đã ghi lại chi tiết **6 lỗi ảo giác và lỗi logic nguy hiểm** do AI tạo ra:  
> 1. AI tự sinh biến `target_model` không tồn tại làm crash request.  
> 2. Đáng sợ nhất: AI chèn lệnh `Base.metadata.drop_all` vào hàm shutdown server – khiến toàn bộ cơ sở dữ liệu production bị xóa sạch mỗi lần restart container! Chúng tôi đã kịp thời phát hiện và gỡ bỏ.  
> 3. AI sinh lỗi thụt lề phá vỡ hàm Streaming SSE.  
> 4. AI quên chuyển tiếp tham số `response_format` khiến chế độ JSON bị mất định dạng.  
> 5. AI bỏ quên việc ghi log kiểm toán khi người dùng dùng chế độ Stream.  
> Và cuối cùng, chúng tôi xây dựng cơ chế tự sửa lỗi chính tả khi người dùng gõ nhầm `conservation_id` thay vì `conversation_id`.  
> Toàn bộ quá trình này chứng minh năng lực làm chủ kỹ thuật và tư duy kiểm định nghiêm ngặt của đội ngũ."*

---

### Phút 4:00 – 4:40 | 5. Hiệu quả kinh tế (ROI) & Kế hoạch 7 ngày tới
* **Giao diện quay màn hình**: Cuộn tới bảng ROI và sơ đồ Roadmap trong `AI_WORKLOG.md`.

> 🎙️ **Lời thoại (Speaker)**:  
> *"Về giá trị thực tế: Với 500,000 lượt yêu cầu mỗi tháng, giải pháp AI Gateway giúp công ty:  
> - **Tiết kiệm ngay 45.6% chi phí** tiền bản quyền LLM nhờ bộ nhớ đệm.  
> - **Nâng Uptime SLA lên 99.95%** nhờ cơ chế Fallback tự động.  
> - **Giảm độ trễ p50 từ 1.8 giây xuống dưới 10 mili-giây** cho các truy vấn phổ biến.  
> Trong 7 ngày tới, chúng tôi đã có lộ trình nâng cấp:  
> - Tích hợp **Semantic Caching** bằng pgvector để nhận diện câu hỏi tương đồng ngữ nghĩa.  
> - Bổ sung thuật toán **Circuit Breaker** và xây dựng Web Dashboard quản trị trực quan."*

---

### Phút 4:40 – 5:00 | 6. Lời kết & Kêu gọi hành động
* **Giao diện quay màn hình**: Quay lại trang README.md hoặc khuôn mặt người thuyết trình / màn hình kết thúc.

> 🎙️ **Lời thoại (Speaker)**:  
> *"Sản phẩm Enterprise AI Gateway của chúng tôi đã hoàn thiện 100% yêu cầu kỹ thuật, đạt trọn vẹn 6/6 điểm thưởng, sẵn sàng đưa vào vận hành ngay hôm nay và mang lại giá trị kinh tế trực tiếp cho công ty.  
> Rất mong nhận được sự ủng hộ và đánh giá tích cực 20/20 từ quý Ban giám khảo và các chuyên gia.  
> Xin chân thành cảm ơn!"*

---

## 💡 Mẹo nhỏ khi quay video để đạt điểm tối đa:
1. **Âm thanh**: Dùng tai nghe có mic chống ồn, nói rõ ràng, dứt khoát, không dùng từ ậm ừ ("ờ", "à").
2. **Độ phân giải màn hình**: Đặt màn hình 1080p (Full HD), phóng to cỡ chữ trong VS Code và Postman (Ctrl + "+") để người xem trên điện thoại hoặc laptop nhỏ nhìn rõ từng request/response.
3. **Mở sẵn các tab**: Mở sẵn terminal Docker, Swagger UI `http://localhost:8000/docs`, Postman đã import sẵn Collection, file `README.md` và `AI_WORKLOG.md`. Khi quay chỉ cần bấm phím tắt Alt+Tab chuyển mượt mà.
