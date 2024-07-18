document.addEventListener("DOMContentLoaded", function () {
  const searchForm = document.getElementById("searchForm");
  const uploadForm = document.getElementById("uploadForm");

  searchForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const query = document.getElementById("query").value;
    const number = document.getElementById("number").value;

    try {
      const response = await fetch("/search_patents", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query, number }),
      });
      const result = await response.json();

      if (result.error) {
        alert(result.error);
      } else {
        const downloadLink = document.getElementById("downloadLink");
        downloadLink.innerHTML = `<a href="/download/${result.excel_file_path}">여기서 EXCEL 파일을 다운로드하세요</a>`;
      }
    } catch (error) {
      console.error("Error:", error);
      alert("검색 및 다운로드에 실패했습니다.");
    }
  });

  uploadForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const fileInput = document.getElementById("file");
    const file = fileInput.files[0];

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("/upload", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();

      if (result.error) {
        alert(result.error);
      } else {
        // 차트 데이터 처리
        const ctx = document.getElementById("myChart").getContext("2d");
        new Chart(ctx, {
          type: "bar",
          data: {
            labels: result.chart_data.labels,
            datasets: [
              {
                label: "단어 빈도수",
                data: result.chart_data.values,
                backgroundColor: "rgba(75, 192, 192, 0.2)",
                borderColor: "rgba(75, 192, 192, 1)",
                borderWidth: 1,
              },
            ],
          },
          options: {
            scales: {
              y: {
                beginAtZero: true,
              },
            },
          },
        });

        // 워드 클라우드 이미지 처리
        const wordcloudImage = document.getElementById("wordcloudImage");
        wordcloudImage.src = `data:image/png;base64,${result.wordcloud}`;

        // 피인용 횟수 상위 10개 특허 시각화
        const topCitedCtx = document
          .getElementById("topCitedChart")
          .getContext("2d");
        new Chart(topCitedCtx, {
          type: "bar",
          data: {
            labels: result.top_cited.labels,
            datasets: [
              {
                label: "피인용 횟수",
                data: result.top_cited.values,
                backgroundColor: "rgba(255, 99, 132, 0.2)",
                borderColor: "rgba(255, 99, 132, 1)",
                borderWidth: 1,
              },
            ],
          },
          options: {
            indexAxis: "y",
            scales: {
              x: {
                beginAtZero: true,
              },
            },
          },
        });
      }
    } catch (error) {
      console.error("Error:", error);
      alert("파일 업로드 또는 분석에 실패했습니다.");
    }
  });
});
