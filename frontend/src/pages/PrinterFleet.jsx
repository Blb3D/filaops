import { useState } from 'react';
import { 
  Printer, Thermometer, Clock, AlertTriangle, CheckCircle2,
  Pause, Play, RotateCcw, Settings, Wifi, WifiOff,
  Droplets, Box, TrendingUp, MoreVertical, Eye,
  Power, Zap, Timer, Target, Layers
} from 'lucide-react';
import './PrinterFleet.css';

const PRINTERS = [
  { 
    id: 'P001', 
    name: 'Prusa MK4 #1', 
    model: 'Prusa MK4',
    status: 'printing',
    connected: true,
    currentJob: {
      id: 'WO-2024-0142',
      product: 'Custom Bracket Assembly',
      progress: 67,
      layer: 234,
      totalLayers: 350,
      timeElapsed: '2h 45m',
      timeRemaining: '1h 20m',
    },
    temps: { bed: 60, hotend: 210, target_bed: 60, target_hotend: 210 },
    material: { type: 'PLA', brand: 'Prusament', color: 'Galaxy Black', remaining: 78 },
    stats: { totalPrints: 1247, successRate: 96.2, hoursRuntime: 3420 }
  },
  { 
    id: 'P002', 
    name: 'Prusa MK4 #2', 
    model: 'Prusa MK4',
    status: 'idle',
    connected: true,
    currentJob: null,
    temps: { bed: 25, hotend: 28, target_bed: 0, target_hotend: 0 },
    material: { type: 'PLA', brand: 'Polymaker', color: 'White', remaining: 45 },
    stats: { totalPrints: 982, successRate: 94.8, hoursRuntime: 2890 }
  },
  { 
    id: 'P003', 
    name: 'Bambu X1C #1', 
    model: 'Bambu Lab X1 Carbon',
    status: 'printing',
    connected: true,
    currentJob: {
      id: 'WO-2024-0139',
      product: 'Sensor Housing v2',
      progress: 89,
      layer: 445,
      totalLayers: 500,
      timeElapsed: '4h 10m',
      timeRemaining: '32m',
    },
    temps: { bed: 80, hotend: 250, target_bed: 80, target_hotend: 250 },
    material: { type: 'PETG', brand: 'Bambu', color: 'Orange', remaining: 62 },
    stats: { totalPrints: 567, successRate: 98.1, hoursRuntime: 1560 }
  },
  { 
    id: 'P004', 
    name: 'Bambu X1C #2', 
    model: 'Bambu Lab X1 Carbon',
    status: 'maintenance',
    connected: true,
    currentJob: null,
    temps: { bed: 25, hotend: 26, target_bed: 0, target_hotend: 0 },
    material: { type: 'ASA', brand: 'Bambu', color: 'Black', remaining: 91 },
    stats: { totalPrints: 423, successRate: 97.4, hoursRuntime: 1120 },
    maintenanceNote: 'Nozzle replacement scheduled'
  },
  { 
    id: 'P005', 
    name: 'Voron 2.4', 
    model: 'Voron 2.4 350mm',
    status: 'printing',
    connected: true,
    currentJob: {
      id: 'WO-2024-0145',
      product: 'Heat Shield Prototype',
      progress: 23,
      layer: 115,
      totalLayers: 500,
      timeElapsed: '1h 45m',
      timeRemaining: '5h 50m',
    },
    temps: { bed: 110, hotend: 260, target_bed: 110, target_hotend: 260 },
    material: { type: 'ASA', brand: 'Polymaker', color: 'Gray', remaining: 55 },
    stats: { totalPrints: 312, successRate: 92.3, hoursRuntime: 980 }
  },
  { 
    id: 'P006', 
    name: 'Ender 3 S1 #1', 
    model: 'Creality Ender 3 S1 Pro',
    status: 'queued',
    connected: true,
    currentJob: {
      id: 'WO-2024-0148',
      product: 'Jig Template Set',
      progress: 0,
      layer: 0,
      totalLayers: 200,
      timeElapsed: '--',
      timeRemaining: '2h 30m',
    },
    temps: { bed: 25, hotend: 27, target_bed: 0, target_hotend: 0 },
    material: { type: 'PLA', brand: 'eSUN', color: 'Blue', remaining: 88 },
    stats: { totalPrints: 1845, successRate: 89.2, hoursRuntime: 5670 }
  },
  { 
    id: 'P007', 
    name: 'Ender 3 S1 #2', 
    model: 'Creality Ender 3 S1 Pro',
    status: 'error',
    connected: true,
    currentJob: {
      id: 'WO-2024-0141',
      product: 'Cable Management Clips',
      progress: 34,
      layer: 68,
      totalLayers: 200,
      timeElapsed: '45m',
      timeRemaining: '--',
    },
    temps: { bed: 55, hotend: 180, target_bed: 60, target_hotend: 210 },
    material: { type: 'PLA', brand: 'Hatchbox', color: 'Black', remaining: 32 },
    stats: { totalPrints: 1623, successRate: 87.1, hoursRuntime: 4980 },
    errorMessage: 'Thermal runaway detected - heater timeout'
  },
  { 
    id: 'P008', 
    name: 'Prusa XL', 
    model: 'Prusa XL 5-tool',
    status: 'printing',
    connected: true,
    currentJob: {
      id: 'WO-2024-0140',
      product: 'Connector Assembly Kit',
      progress: 52,
      layer: 260,
      totalLayers: 500,
      timeElapsed: '3h 20m',
      timeRemaining: '3h 05m',
    },
    temps: { bed: 60, hotend: 215, target_bed: 60, target_hotend: 215 },
    material: { type: 'PLA', brand: 'Prusament', color: 'Jet Black', remaining: 67 },
    stats: { totalPrints: 234, successRate: 95.7, hoursRuntime: 720 }
  },
];

function PrinterFleet() {
  const [selectedPrinter, setSelectedPrinter] = useState(null);

  const getStatusColor = (status) => {
    const colors = {
      printing: '#3b82f6',
      idle: '#6b7280',
      maintenance: '#f59e0b',
      queued: '#8b5cf6',
      error: '#ef4444',
    };
    return colors[status] || '#6b7280';
  };

  const getStatusClass = (status) => {
    return `status-${status}`;
  };

  const formatTemp = (current, target) => {
    if (target === 0) return `${current}°`;
    return `${current}° / ${target}°`;
  };

  return (
    <div className="printer-fleet">
      {/* Header */}
      <header className="fleet-header">
        <div className="header-left">
          <h1>Printer Fleet</h1>
          <p className="header-subtitle">Monitor and manage your print farm</p>
        </div>
        <div className="header-stats">
          <div className="mini-stat">
            <span className="mini-stat-value printing">
              {PRINTERS.filter(p => p.status === 'printing').length}
            </span>
            <span className="mini-stat-label">Printing</span>
          </div>
          <div className="mini-stat">
            <span className="mini-stat-value idle">
              {PRINTERS.filter(p => p.status === 'idle').length}
            </span>
            <span className="mini-stat-label">Idle</span>
          </div>
          <div className="mini-stat">
            <span className="mini-stat-value error">
              {PRINTERS.filter(p => p.status === 'error').length}
            </span>
            <span className="mini-stat-label">Error</span>
          </div>
        </div>
      </header>

      {/* Printer Grid */}
      <div className="fleet-grid">
        {PRINTERS.map(printer => (
          <div 
            key={printer.id} 
            className={`printer-card ${getStatusClass(printer.status)}`}
            onClick={() => setSelectedPrinter(printer)}
          >
            {/* Status Indicator */}
            <div 
              className="printer-status-bar"
              style={{ backgroundColor: getStatusColor(printer.status) }}
            />

            {/* Card Header */}
            <div className="printer-card-header">
              <div className="printer-identity">
                <span className="printer-id">{printer.id}</span>
                <h3 className="printer-name">{printer.name}</h3>
                <span className="printer-model">{printer.model}</span>
              </div>
              <div className="printer-connection">
                {printer.connected ? (
                  <Wifi size={16} className="connected" />
                ) : (
                  <WifiOff size={16} className="disconnected" />
                )}
              </div>
            </div>

            {/* Status Badge */}
            <div className={`printer-status-badge ${printer.status}`}>
              {printer.status === 'printing' && <Play size={12} />}
              {printer.status === 'idle' && <Pause size={12} />}
              {printer.status === 'maintenance' && <Settings size={12} />}
              {printer.status === 'queued' && <Clock size={12} />}
              {printer.status === 'error' && <AlertTriangle size={12} />}
              <span>{printer.status}</span>
            </div>

            {/* Current Job (if any) */}
            {printer.currentJob && (
              <div className="printer-job">
                <div className="job-info">
                  <span className="job-id">{printer.currentJob.id}</span>
                  <span className="job-name">{printer.currentJob.product}</span>
                </div>
                {printer.status === 'printing' && (
                  <>
                    <div className="job-progress-container">
                      <div 
                        className="job-progress-bar"
                        style={{ width: `${printer.currentJob.progress}%` }}
                      />
                    </div>
                    <div className="job-details">
                      <span className="job-progress-text">
                        {printer.currentJob.progress}%
                      </span>
                      <span className="job-layer">
                        <Layers size={12} />
                        {printer.currentJob.layer}/{printer.currentJob.totalLayers}
                      </span>
                    </div>
                  </>
                )}
                {printer.status === 'error' && (
                  <div className="error-message">
                    <AlertTriangle size={14} />
                    <span>{printer.errorMessage}</span>
                  </div>
                )}
              </div>
            )}

            {/* Temperatures */}
            <div className="printer-temps">
              <div className="temp-item">
                <Thermometer size={14} className="temp-icon hotend" />
                <span className="temp-label">Hotend</span>
                <span className="temp-value">
                  {formatTemp(printer.temps.hotend, printer.temps.target_hotend)}
                </span>
              </div>
              <div className="temp-item">
                <Box size={14} className="temp-icon bed" />
                <span className="temp-label">Bed</span>
                <span className="temp-value">
                  {formatTemp(printer.temps.bed, printer.temps.target_bed)}
                </span>
              </div>
            </div>

            {/* Material */}
            <div className="printer-material">
              <Droplets size={14} />
              <span className="material-type">{printer.material.type}</span>
              <span className="material-color">{printer.material.color}</span>
              <div className="material-remaining">
                <div 
                  className="material-bar"
                  style={{ width: `${printer.material.remaining}%` }}
                />
              </div>
              <span className="material-percent">{printer.material.remaining}%</span>
            </div>

            {/* Time Info (for active prints) */}
            {printer.currentJob && printer.status === 'printing' && (
              <div className="printer-time">
                <div className="time-item">
                  <Timer size={12} />
                  <span>Elapsed: {printer.currentJob.timeElapsed}</span>
                </div>
                <div className="time-item remaining">
                  <Clock size={12} />
                  <span>Remaining: {printer.currentJob.timeRemaining}</span>
                </div>
              </div>
            )}

            {/* Maintenance Note */}
            {printer.status === 'maintenance' && printer.maintenanceNote && (
              <div className="maintenance-note">
                <Settings size={14} />
                <span>{printer.maintenanceNote}</span>
              </div>
            )}

            {/* Quick Actions */}
            <div className="printer-actions">
              {printer.status === 'printing' && (
                <>
                  <button className="action-btn" title="Pause Print">
                    <Pause size={14} />
                  </button>
                  <button className="action-btn" title="View Details">
                    <Eye size={14} />
                  </button>
                </>
              )}
              {printer.status === 'idle' && (
                <button className="action-btn primary" title="Start Job">
                  <Play size={14} />
                  <span>Assign Job</span>
                </button>
              )}
              {printer.status === 'error' && (
                <>
                  <button className="action-btn warning" title="Retry">
                    <RotateCcw size={14} />
                  </button>
                  <button className="action-btn danger" title="Cancel">
                    <Power size={14} />
                  </button>
                </>
              )}
              <button className="action-btn more" title="More Options">
                <MoreVertical size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Printer Detail Modal */}
      {selectedPrinter && (
        <div className="printer-modal-overlay" onClick={() => setSelectedPrinter(null)}>
          <div className="printer-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div 
                className="modal-status-indicator"
                style={{ backgroundColor: getStatusColor(selectedPrinter.status) }}
              />
              <div className="modal-title">
                <h2>{selectedPrinter.name}</h2>
                <p>{selectedPrinter.model}</p>
              </div>
              <div className={`modal-status-badge ${selectedPrinter.status}`}>
                {selectedPrinter.status}
              </div>
            </div>

            <div className="modal-content">
              {/* Current Job Section */}
              {selectedPrinter.currentJob && (
                <div className="modal-section">
                  <h3>Current Job</h3>
                  <div className="current-job-card">
                    <div className="job-header">
                      <span className="job-id">{selectedPrinter.currentJob.id}</span>
                      <span className="job-name">{selectedPrinter.currentJob.product}</span>
                    </div>
                    {selectedPrinter.status === 'printing' && (
                      <>
                        <div className="progress-section">
                          <div className="progress-header">
                            <span>Progress</span>
                            <span className="progress-percent">{selectedPrinter.currentJob.progress}%</span>
                          </div>
                          <div className="progress-bar-large">
                            <div 
                              className="progress-fill"
                              style={{ width: `${selectedPrinter.currentJob.progress}%` }}
                            />
                          </div>
                        </div>
                        <div className="job-stats-grid">
                          <div className="job-stat">
                            <Layers size={16} />
                            <span className="stat-label">Layer</span>
                            <span className="stat-value">{selectedPrinter.currentJob.layer} / {selectedPrinter.currentJob.totalLayers}</span>
                          </div>
                          <div className="job-stat">
                            <Timer size={16} />
                            <span className="stat-label">Elapsed</span>
                            <span className="stat-value">{selectedPrinter.currentJob.timeElapsed}</span>
                          </div>
                          <div className="job-stat">
                            <Clock size={16} />
                            <span className="stat-label">Remaining</span>
                            <span className="stat-value">{selectedPrinter.currentJob.timeRemaining}</span>
                          </div>
                          <div className="job-stat">
                            <Target size={16} />
                            <span className="stat-label">ETA</span>
                            <span className="stat-value">~{selectedPrinter.currentJob.timeRemaining}</span>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Temperature Section */}
              <div className="modal-section">
                <h3>Temperatures</h3>
                <div className="temp-cards">
                  <div className="temp-card hotend">
                    <Thermometer size={24} />
                    <div className="temp-info">
                      <span className="temp-name">Hotend</span>
                      <span className="temp-current">{selectedPrinter.temps.hotend}°C</span>
                      {selectedPrinter.temps.target_hotend > 0 && (
                        <span className="temp-target">Target: {selectedPrinter.temps.target_hotend}°C</span>
                      )}
                    </div>
                    <div className="temp-gauge">
                      <div 
                        className="temp-fill"
                        style={{ height: `${Math.min((selectedPrinter.temps.hotend / 300) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="temp-card bed">
                    <Box size={24} />
                    <div className="temp-info">
                      <span className="temp-name">Bed</span>
                      <span className="temp-current">{selectedPrinter.temps.bed}°C</span>
                      {selectedPrinter.temps.target_bed > 0 && (
                        <span className="temp-target">Target: {selectedPrinter.temps.target_bed}°C</span>
                      )}
                    </div>
                    <div className="temp-gauge">
                      <div 
                        className="temp-fill"
                        style={{ height: `${Math.min((selectedPrinter.temps.bed / 120) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Material Section */}
              <div className="modal-section">
                <h3>Material</h3>
                <div className="material-card">
                  <div className="material-info">
                    <span className="material-type-large">{selectedPrinter.material.type}</span>
                    <span className="material-brand">{selectedPrinter.material.brand}</span>
                    <span className="material-color-label">{selectedPrinter.material.color}</span>
                  </div>
                  <div className="material-remaining-large">
                    <div className="remaining-circle">
                      <svg viewBox="0 0 36 36">
                        <path
                          className="circle-bg"
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                        <path
                          className="circle-fill"
                          strokeDasharray={`${selectedPrinter.material.remaining}, 100`}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                      </svg>
                      <span className="remaining-percent">{selectedPrinter.material.remaining}%</span>
                    </div>
                    <span className="remaining-label">Remaining</span>
                  </div>
                </div>
              </div>

              {/* Printer Stats */}
              <div className="modal-section">
                <h3>Performance Stats</h3>
                <div className="stats-grid">
                  <div className="stat-card">
                    <TrendingUp size={20} />
                    <span className="stat-value">{selectedPrinter.stats.totalPrints.toLocaleString()}</span>
                    <span className="stat-label">Total Prints</span>
                  </div>
                  <div className="stat-card">
                    <CheckCircle2 size={20} />
                    <span className="stat-value">{selectedPrinter.stats.successRate}%</span>
                    <span className="stat-label">Success Rate</span>
                  </div>
                  <div className="stat-card">
                    <Clock size={20} />
                    <span className="stat-value">{selectedPrinter.stats.hoursRuntime.toLocaleString()}h</span>
                    <span className="stat-label">Runtime</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="modal-actions">
              {selectedPrinter.status === 'printing' && (
                <>
                  <button className="modal-btn secondary">
                    <Pause size={16} />
                    Pause
                  </button>
                  <button className="modal-btn danger">
                    <Power size={16} />
                    Cancel
                  </button>
                </>
              )}
              {selectedPrinter.status === 'idle' && (
                <button className="modal-btn primary">
                  <Play size={16} />
                  Assign Job
                </button>
              )}
              {selectedPrinter.status === 'error' && (
                <>
                  <button className="modal-btn warning">
                    <RotateCcw size={16} />
                    Retry
                  </button>
                  <button className="modal-btn secondary">
                    <Zap size={16} />
                    Clear Error
                  </button>
                </>
              )}
              <button className="modal-btn secondary">
                <Settings size={16} />
                Settings
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PrinterFleet;
