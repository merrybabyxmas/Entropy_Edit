import { useState, useEffect, useCallback } from 'react';
import { NeuPanel, NeuButton } from './NeuComponents';
import { FolderOpen, Settings, Play, Menu, Download, Loader } from 'lucide-react';
import CurveEditor from './CurveEditor';
import AssetBrowser from './AssetBrowser';
import PropertiesPanel, { type PropertyState } from './PropertiesPanel';
import Timeline, { type ClipBlock } from './Timeline';
import axios from 'axios';
import debounce from 'lodash/debounce';

const Layout = () => {
  // --- State Definitions ---

  // Curve Data
  const [curveData, setCurveData] = useState<any[]>([]);
  const [nodeData, setNodeData] = useState<any[]>([]);
  const [edlClips, setEdlClips] = useState<ClipBlock[]>([]);

  // Properties (Sliders)
  const [properties, setProperties] = useState<PropertyState>({
      sigma: 30,
      height: 80,
      position: 180,
      perturbation: 0,
      jitter: 100
  });

  // Timeline
  const [currentTime, setCurrentTime] = useState<number>(0);
  const DURATION = 100; // Fixed Duration for prototype

  // UI State
  const [isRendering, setIsRendering] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  // --- Handlers ---

  const handlePropertyChange = (key: keyof PropertyState, value: number) => {
      setProperties(prev => ({ ...prev, [key]: value }));
  };

  // --- Preview Logic ---

  // Helper to get curve value at current time (Linear Interpolation for prototype)
  const getCurveValueAtTime = (t: number) => {
       // t is 0-DURATION
       // curveData points are 0-1 normalized
       const normalizedT = t / DURATION;

       // Sort points by X
       const sorted = [...curveData].sort((a, b) => a.x - b.x);
       if (sorted.length === 0) return 0.5;

       // Find segment
       for (let i = 0; i < sorted.length - 1; i++) {
           if (normalizedT >= sorted[i].x && normalizedT <= sorted[i+1].x) {
               const range = sorted[i+1].x - sorted[i].x;
               const diff = normalizedT - sorted[i].x;
               const ratio = diff / range;
               // Linear lerp Y
               return sorted[i].y + (sorted[i+1].y - sorted[i].y) * ratio;
           }
       }

       // Clamp
       if (normalizedT < sorted[0].x) return sorted[0].y;
       if (normalizedT > sorted[sorted.length-1].x) return sorted[sorted.length-1].y;

       return 0.5;
  };

  const fetchPreview = async (
      t: number,
      cData: any[],
      nData: any[],
      props: PropertyState
  ) => {
      setIsPreviewLoading(true);
      try {
          const nodesPayload = nData.map((n: any) => ({
             peak_t: n.peak_t,
             sigma: n.sigma || props.sigma,
             amplitude: n.amplitude
          }));

          const sampledCurve = [];
          if (cData.length > 0) {
             cData.forEach((p: any) => {
                 sampledCurve.push({ time: p.x, value: p.y });
             });
          } else {
              sampledCurve.push({time: 0, value: 0.5}, {time: 1, value: 0.5});
          }

          const res = await axios.post('http://localhost:8000/preview', {
              timestamp: t / DURATION,
              curve_data: sampledCurve,
              nodes: nodesPayload,
              duration: DURATION
          }, { responseType: 'blob' });

          const url = URL.createObjectURL(res.data);
          setPreviewUrl(url);

      } catch (e) {
          console.error("Preview fetch failed", e);
      } finally {
          setIsPreviewLoading(false);
      }
  };

  const fetchEDL = async (cData: any[], nData: any[], props: PropertyState) => {
       try {
          const nodesPayload = nData.map((n: any) => ({
             peak_t: n.peak_t,
             sigma: n.sigma || props.sigma,
             amplitude: n.amplitude
          }));
          const sampledCurve = [];
          if (cData.length > 0) {
             cData.forEach((p: any) => {
                 sampledCurve.push({ time: p.x, value: p.y });
             });
          } else {
              sampledCurve.push({time: 0, value: 0.5}, {time: 1, value: 0.5});
          }

          const res = await axios.post('http://localhost:8000/edl', {
              curve_data: sampledCurve,
              nodes: nodesPayload,
              target_length: DURATION
          });

          if (res.data.edl) {
              setEdlClips(res.data.edl);
          }
       } catch(e) {
           console.error("EDL fetch failed", e);
       }
  };

  const debouncedPreview = useCallback(
      debounce((t, c, n, p) => fetchPreview(t, c, n, p), 300),
      []
  );

  const debouncedEDL = useCallback(
      debounce((c, n, p) => fetchEDL(c, n, p), 500),
      []
  );

  // Trigger Preview on Time change or curve change
  useEffect(() => {
      debouncedPreview(currentTime, curveData, nodeData, properties);
  }, [currentTime, curveData, nodeData, properties, debouncedPreview]);

  // Trigger EDL update only on curve/property change (not time)
  useEffect(() => {
      debouncedEDL(curveData, nodeData, properties);
  }, [curveData, nodeData, properties, debouncedEDL]);


  // --- Render Logic ---

  const handleRender = async () => {
      setIsRendering(true);
      try {
          const sampledCurve = [];
          if (curveData.length > 0) {
              // Sample at intervals or just pass points if backend supports interpolation
              // Backend match_clips_to_curve expects points.
             curveData.forEach((p: any) => {
                 sampledCurve.push({ time: p.x, value: p.y });
             });
          } else {
              // Default flat curve
              sampledCurve.push({time: 0, value: 0.5}, {time: 1, value: 0.5});
          }

          const nodes = nodeData.map((n: any) => ({
             peak_t: n.peak_t,
             sigma: n.sigma || properties.sigma,
             amplitude: n.amplitude
          }));

          const payload = {
              curve_data: sampledCurve,
              nodes: nodes,
              target_length: DURATION / 10.0 // Just a scaling factor for demo
          };

          const res = await axios.post('http://localhost:8000/render', payload);
          alert(`Render Complete: ${res.data.output_path}`);
      } catch (e) {
          console.error(e);
          alert("Render failed");
      } finally {
          setIsRendering(false);
      }
  };

  return (
    <div className="flex flex-col h-screen w-screen p-4 gap-4 bg-background overflow-hidden text-sm">
      {/* Top Bar */}
      <div className="flex justify-between items-center h-12">
        <div className="flex gap-4 items-center">
          <NeuButton className="w-10 h-10 p-0 flex items-center justify-center"><Menu size={18}/></NeuButton>
          <NeuButton className="w-10 h-10 p-0 flex items-center justify-center"><FolderOpen size={18}/></NeuButton>
          <NeuButton className="w-10 h-10 p-0 flex items-center justify-center"><Settings size={18}/></NeuButton>
        </div>
        <h1 className="text-xl font-bold tracking-wider text-text">LAVA Edit</h1>
        <div className="flex gap-4 items-center">
           <NeuButton
             className="w-10 h-10 p-0 flex items-center justify-center text-primary"
             onClick={handleRender}
             disabled={isRendering}
           >
             {isRendering ? <Loader className="animate-spin" size={18}/> : <Download size={18}/>}
           </NeuButton>
        </div>
      </div>

      {/* Main Grid */}
      <div className="flex flex-1 gap-4 min-h-0">

        {/* Left/Center: Preview & Editors */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">

          {/* Preview Area */}
          <NeuPanel className="flex-1 flex flex-col items-center justify-center relative min-h-[300px]" inset>
            <div className="w-[80%] h-[80%] bg-black rounded-lg relative overflow-hidden shadow-2xl flex items-center justify-center">
               {/* Image Display */}
               {previewUrl ? (
                   <img src={previewUrl} className="w-full h-full object-contain" alt="Preview" />
               ) : (
                   <div className="text-gray-500 flex flex-col items-center">
                       <Play size={48} className="opacity-20 mb-2" />
                       <span>No Preview</span>
                   </div>
               )}

               {/* Loading Overlay */}
               {isPreviewLoading && (
                   <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                       <Loader className="animate-spin text-white" />
                   </div>
               )}

               {/* Overlay Info */}
               <div className="absolute top-4 left-4 bg-black/50 text-white px-2 py-1 rounded text-xs pointer-events-none">
                  T: {currentTime.toFixed(1)} / {DURATION}
               </div>
            </div>
          </NeuPanel>

          {/* Curve Editors */}
          <div className="h-48 flex gap-4">
             <NeuPanel className="flex-1 relative">
                <div className="absolute top-2 left-4 text-xs font-bold text-gray-500">Similarity Control</div>
                <CurveEditor type="bezier" onChange={setCurveData} />
             </NeuPanel>
             <NeuPanel className="flex-1 relative">
                <div className="absolute top-2 left-4 text-xs font-bold text-gray-500">Noise Control</div>
                <CurveEditor type="gaussian" onChange={setNodeData} />
             </NeuPanel>
          </div>

          {/* Timeline */}
          <NeuPanel className="h-32" inset>
             <Timeline
                currentTime={currentTime}
                duration={DURATION}
                onTimeChange={setCurrentTime}
                clips={edlClips}
             />
          </NeuPanel>

        </div>

        {/* Right Sidebar */}
        <div className="w-72 flex flex-col gap-4">
          <NeuPanel className="flex-1 flex flex-col gap-2 min-h-0" inset>
             <div className="flex justify-between items-center px-2">
               <span className="text-xs font-bold text-gray-500">File Browser</span>
             </div>
             <AssetBrowser />
          </NeuPanel>

          <NeuPanel className="h-1/2">
             <PropertiesPanel values={properties} onChange={handlePropertyChange} />
          </NeuPanel>
        </div>

      </div>
    </div>
  );
};

export default Layout;
