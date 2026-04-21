<template>
  <div>
    <table class="stock-table">
      <thead>
        <tr>
          <th>代碼</th>
          <th>名稱</th>
          <th>散戶比例</th>
          <th>大戶比例</th>
          <!-- 其他欄位 -->
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="stock in stocks" :key="stock.stock_id">
          <td>{{ stock.stock_id }}</td>
          <td>{{ stock.stock_name }}</td>
          <td>{{ stock.retail_percent }}%</td>
          <td>{{ stock.large_percent }}%</td>
          <!-- 其他欄位 -->
          <td>
            <button @click="viewChart(stock.stock_id, stock.stock_name)" class="btn-chart">
              查看走勢
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    
    <!-- 股價圖表彈出視窗 -->
    <div v-if="showModal" class="modal">
      <div class="modal-content">
        <span class="close" @click="closeModal">&times;</span>
        <h3>{{ selectedStock.name }} ({{ selectedStock.id }}) 近一個月走勢</h3>
        <div v-if="loading">載入中...</div>
        <div v-else-if="chartError" class="error">{{ chartError }}</div>
        <div v-else id="stock-chart" style="width:100%; height:400px;"></div>
      </div>
    </div>
  </div>
</template>

<script>
import Plotly from 'plotly.js-dist';

export default {
  data() {
    return {
      stocks: [],
      showModal: false,
      loading: false,
      chartError: null,
      selectedStock: {
        id: '',
        name: ''
      }
    };
  },
  methods: {
    async viewChart(stockId, stockName) {
      this.selectedStock = {
        id: stockId,
        name: stockName
      };
      this.showModal = true;
      this.loading = true;
      this.chartError = null;
      
      try {
        const response = await fetch(`/api/stock_price/${stockId}`);
        const result = await response.json();
        
        if (result.status === 'success') {
          this.loading = false;
          // 等 DOM 更新後再渲染圖表
          this.$nextTick(() => {
            const chartElement = document.getElementById('stock-chart');
            if (chartElement) {
              const chartData = JSON.parse(result.chart);
              Plotly.newPlot('stock-chart', chartData.data, chartData.layout);
            }
          });
        } else {
          this.chartError = result.message || '無法載入股價數據';
          this.loading = false;
        }
      } catch (error) {
        this.chartError = '發生錯誤，無法載入股價數據';
        this.loading = false;
        console.error('Error loading stock chart:', error);
      }
    },
    closeModal() {
      this.showModal = false;
    }
  }
}
</script>

<style scoped>
.stock-table {
  width: 100%;
  border-collapse: collapse;
}
.stock-table th, .stock-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
}
.btn-chart {
  background-color: #4CAF50;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-chart:hover {
  background-color: #45a049;
}

.modal {
  position: fixed;
  z-index: 1;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-content {
  background-color: #fefefe;
  padding: 20px;
  border-radius: 5px;
  width: 80%;
  max-width: 800px;
}
.close {
  color: #aaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
  cursor: pointer;
}
.error {
  color: red;
  text-align: center;
  padding: 20px;
}
</style>