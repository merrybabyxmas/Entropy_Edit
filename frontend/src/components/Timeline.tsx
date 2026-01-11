import React, { useRef } from 'react';

export interface ClipBlock {
    timeline_start: number;
    duration: number;
    similarity_score: number;
    source_clip_id: string;
}

interface TimelineProps {
    currentTime: number;
    duration?: number;
    onTimeChange: (time: number) => void;
    clips?: ClipBlock[];
}

const Timeline: React.FC<TimelineProps> = ({ currentTime, duration = 100, onTimeChange, clips = [] }) => {
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
            <div className="flex gap-2 items-center pointer-events-none">
                 <div className="w-20 text-[10px] font-bold text-gray-500">Main Channel</div>
                 <div className="flex-1 h-10 bg-gray-200/50 rounded-lg relative shadow-inner overflow-hidden">
                     {clips.map((clip, idx) => (
                         <div
                            key={idx}
                            className="absolute h-full top-0 border-r border-white/20 flex items-center justify-center text-[8px] text-white truncate px-1 transition-all"
                            style={{
                                left: `${(clip.timeline_start / duration) * 100}%`,
                                width: `${(clip.duration / duration) * 100}%`,
                                backgroundColor: `rgba(77, 124, 254, ${0.3 + clip.similarity_score * 0.7})` // Opacity based on score
                            }}
                            title={`${clip.source_clip_id} (Sim: ${clip.similarity_score.toFixed(2)})`}
                         >
                            {clip.source_clip_id}
                         </div>
                     ))}
                 </div>
            </div>

            <div className="flex gap-2 items-center pointer-events-none opacity-50">
                 <div className="w-20 text-[10px] font-bold text-gray-500">Overlay Channel</div>
                 <div className="flex-1 h-10 bg-gray-200/50 rounded-lg flex items-center p-1 gap-1 shadow-inner relative">
                      {/* Placeholder for future overlay implementation */}
                      <div className="absolute left-[20%] h-8 w-16 bg-orange-400 rounded shadow-sm border border-orange-300 flex items-center justify-center text-[8px] text-white">Overlay</div>
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
