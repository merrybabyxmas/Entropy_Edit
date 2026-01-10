import React, { useRef } from 'react';

interface TimelineProps {
    currentTime: number;
    duration?: number;
    onTimeChange: (time: number) => void;
}

const Timeline: React.FC<TimelineProps> = ({ currentTime, duration = 100, onTimeChange }) => {
    const containerRef = useRef<HTMLDivElement>(null);

    const handleInteract = (e: React.MouseEvent) => {
        if (!containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const width = rect.width;

        // Calculate percentage
        const pct = Math.max(0, Math.min(1, x / width));
        const newTime = pct * duration;
        onTimeChange(newTime);
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (e.buttons === 1) {
            handleInteract(e);
        }
    };

    return (
        <div
            className="w-full h-full p-2 flex flex-col gap-2 relative overflow-hidden select-none"
            onMouseDown={handleInteract}
            onMouseMove={handleMouseMove}
            ref={containerRef}
        >
            {/* Time Ruler */}
            <div className="flex h-4 text-[10px] text-gray-400 border-b border-gray-300 pointer-events-none">
                {[0, 0.2, 0.4, 0.6, 0.8, 1.0].map(t => (
                    <div key={t} className="flex-1 border-l border-gray-300 pl-1">{(t * duration).toFixed(0)}</div>
                ))}
            </div>

            {/* Tracks */}
            <div className="flex gap-2 items-center pointer-events-none opacity-50">
                 <div className="w-20 text-[10px] font-bold text-gray-500">Main Channel</div>
                 <div className="flex-1 h-10 bg-gray-200/50 rounded-lg flex items-center p-1 gap-1 shadow-inner relative">
                     <div className="h-8 w-16 bg-blue-400 rounded shadow-sm border border-blue-300 flex items-center justify-center text-[8px] text-white">Clip 1</div>
                     <div className="h-8 w-12 bg-blue-400 rounded shadow-sm border border-blue-300"></div>
                     <div className="h-8 w-20 bg-blue-400 rounded shadow-sm border border-blue-300"></div>
                 </div>
            </div>

            <div className="flex gap-2 items-center pointer-events-none opacity-50">
                 <div className="w-20 text-[10px] font-bold text-gray-500">Overlay Channel</div>
                 <div className="flex-1 h-10 bg-gray-200/50 rounded-lg flex items-center p-1 gap-1 shadow-inner relative">
                      <div className="absolute left-[20%] h-8 w-16 bg-orange-400 rounded shadow-sm border border-orange-300 flex items-center justify-center text-[8px] text-white">Clip A</div>
                 </div>
            </div>

            {/* Playhead */}
            <div
                className="absolute top-0 bottom-0 w-px bg-primary z-20 pointer-events-none transition-all duration-75"
                style={{ left: `${(currentTime / duration) * 100}%` }}
            >
                <div className="w-3 h-3 bg-primary rounded-full -ml-[5px] -mt-1 shadow-md"></div>
            </div>

        </div>
    );
};

export default Timeline;
