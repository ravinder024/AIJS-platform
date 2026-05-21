# Job Scraper Web Interface

A simple, user-friendly web interface for the Python job scraper that searches across multiple job boards.

## 🚀 Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Web Server:**
   ```bash
   python app.py
   ```

3. **Open Your Browser:**
   - Navigate to: `http://localhost:5000`
   - The web interface will load automatically

## 🎯 Features

### **Search Form**
- **Job Title/Keyword** *(required)*: Enter the position you're looking for
- **Location** *(required)*: Specify location or "Remote" for remote jobs
- **Posted Within**: Filter by how recently jobs were posted (1-30 days)
- **Work Setting**: Filter by remote, hybrid, or on-site positions
- **Exclude Keywords**: Comma-separated list of terms to avoid
- **Company Size**: Optional company size preference
- **Job Sources**: Select which job boards to search

### **Search Results**
- **Truncated Display**: Shows first 20 results for quick browsing
- **Job Cards**: Clean cards showing title, company, location, and description preview
- **Source Tags**: Each job shows which platform it came from

### **Export Options**
- **JSON Export**: Download complete results as structured JSON file
- **CSV Export**: Download results as spreadsheet-compatible CSV file
- **Timestamped Files**: All exports include timestamp in filename

## 🌐 Supported Job Boards

| Platform | Status | Notes |
|----------|--------|-------|
| **RemoteOK** | ✅ Working | Best for remote positions |
| **Naukri** | ⚠️ Limited | May need URL adjustments |
| **Indeed** | ⚠️ Blocked | Anti-bot protection |
| **Wellfound** | ⚠️ Blocked | Anti-bot protection |
| **LinkedIn** | 📝 Placeholder | Requires authentication |

## 📱 Responsive Design

- **Mobile-Friendly**: Works on phones, tablets, and desktops
- **Modern UI**: Clean, professional interface
- **Real-time Feedback**: Loading states and error messages
- **Accessible**: Keyboard navigation and screen reader friendly

## 🛠️ Technical Details

### **Backend (Flask)**
- **Route `/`**: Main search form page
- **Route `/search`**: POST endpoint for job searches
- **Route `/export/<format>`**: Download results as JSON/CSV

### **Frontend (Vanilla JS)**
- **Form Validation**: Client-side validation for required fields
- **AJAX Requests**: Asynchronous search without page reload
- **Dynamic UI**: Real-time results display and export functionality

### **Data Flow**
1. User fills search form
2. Frontend sends AJAX request to `/search`
3. Backend runs scrapers based on selected sources
4. Results filtered, deduplicated, and returned
5. Frontend displays results in card format
6. Export buttons generate downloadable files

## 🔧 Configuration

### **Default Settings**
- **Port**: 5000 (configurable in `app.py`)
- **Host**: 0.0.0.0 (accessible from network)
- **Debug Mode**: Enabled for development

### **Customization**
- **Styling**: Edit CSS in `templates/index.html`
- **Job Sources**: Add new scrapers to `SCRAPERS` dict in `app.py`
- **Results Limit**: Change `display_jobs = unique_jobs[:20]` in `app.py`

## 📊 Example Usage

1. **Search for Remote Developer Jobs:**
   - Keyword: "Frontend Developer"
   - Location: "Remote"
   - Sources: RemoteOK
   - Posted Within: Last week

2. **Export Results:**
   - Click "Export JSON" for complete data
   - Click "Export CSV" for spreadsheet analysis

3. **Filter Unwanted Jobs:**
   - Exclude Keywords: "night shift, 6-day work week"
   - Work Setting: "Remote" only

## 🚨 Common Issues

### **No Jobs Found**
- Try broader keywords ("Developer" instead of "Senior React Developer")
- Check if selected job boards are working (start with RemoteOK)
- Increase "Posted Within" timeframe

### **403 Forbidden Errors**
- Expected for Indeed/Wellfound (anti-bot protection)
- Use RemoteOK or Naukri for reliable results
- Consider adding user-agent rotation for better success

### **Unicode Display Issues**
- Emojis may not display correctly in Windows console
- Web interface displays properly in all browsers
- Check log files for complete error details

## 🎯 Next Steps

1. **Add More Job Boards**: Implement new scrapers using the modular structure
2. **User Authentication**: Save search preferences and history
3. **Advanced Filters**: Salary ranges, company ratings, job types
4. **Real-time Updates**: WebSocket integration for live job feeds
5. **API Keys**: Integration with official job board APIs where available