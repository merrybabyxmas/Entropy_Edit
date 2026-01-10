import React, { useState } from 'react';
import { NeuPanel, NeuButton } from './NeuComponents';
import { FolderOpen, Settings, Play, Menu, Download, Loader } from 'lucide-react';
import CurveEditor from './CurveEditor';
import AssetBrowser from './AssetBrowser';
import PropertiesPanel from './PropertiesPanel';
import Timeline from './Timeline';
import axios from 'axios';

const Layout = () => {
  // State for rendering
  const [curveData, setCurveData] = useState<any>(null);
  const [nodeData, setNodeData] = useState<any>(null);
  const [isRendering, setIsRendering] = useState(false);

  const handleRender = async () => {
      setIsRendering(true);
      try {
          // Transform curveData (points) into the format expected by backend
          // Backend expects curve_data list of {time, value}
          const sampledCurve = [];
          if (curveData) {
             curveData.forEach((p: any) => {
                 sampledCurve.push({ time: p.x, value: p.y });
             });
          }

          const nodes = nodeData ? nodeData.map((n: any) => ({
             peak_t: n.peak_t,
             sigma: n.sigma,
             amplitude: n.amplitude
          })) : [];

          const payload = {
              curve_data: sampledCurve,
              nodes: nodes,
              target_length: 10.0 // Fixed for demo
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
            <div className="w-[80%] h-[80%] bg-black rounded-lg relative overflow-hidden shadow-2xl">
              {/* Placeholder Video Overlay */}
               <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                  <Play size={48} className="opacity-20" />
               </div>
               {/* Selection Box Mockup */}
               <div className="absolute top-[30%] left-[40%] w-32 h-20 border-2 border-primary rounded flex items-center justify-center">
                  <span className="bg-white/80 text-xs px-1 rounded">x: 250, y: 180</span>
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
             <Timeline />
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
             <PropertiesPanel />
          </NeuPanel>
        </div>

      </div>
    </div>
  );
};

export default Layout;
