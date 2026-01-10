import React from 'react';

const Timeline: React.FC = () => {
    return (
        <div className="w-full h-full p-2 flex flex-col gap-2 relative overflow-x-auto">
            {/* Time Ruler */}
            <div className="flex h-4 text-[10px] text-gray-400 border-b border-gray-300">
                {[0, 100, 200, 300, 400, 500, 600, 700].map(t => (
                    <div key={t} className="flex-1 border-l border-gray-300 pl-1">{t}</div>
                ))}
            </div>

            {/* Tracks */}
            <div className="flex gap-2 items-center">
                 <div className="w-20 text-[10px] font-bold text-gray-500">Main Channel</div>
                 <div className="flex-1 h-10 bg-gray-200/50 rounded-lg flex items-center p-1 gap-1 shadow-inner relative">
                     {/* Mock Clips */}
                     <div className="h-8 w-16 bg-blue-400 rounded shadow-sm border border-blue-300 flex items-center justify-center text-[8px] text-white">Clip 1</div>
                     <div className="h-8 w-12 bg-blue-400 rounded shadow-sm border border-blue-300"></div>
                     <div className="h-8 w-20 bg-blue-400 rounded shadow-sm border border-blue-300"></div>
                     <div className="h-8 w-24 bg-blue-400 rounded shadow-sm border border-blue-300"></div>
                 </div>
            </div>

            <div className="flex gap-2 items-center">
                 <div className="w-20 text-[10px] font-bold text-gray-500">Overlay Channel</div>
                 <div className="flex-1 h-10 bg-gray-200/50 rounded-lg flex items-center p-1 gap-1 shadow-inner relative">
                      {/* Mock Clips */}
                      <div className="absolute left-[20%] h-8 w-16 bg-orange-400 rounded shadow-sm border border-orange-300 flex items-center justify-center text-[8px] text-white">Clip A</div>
                      <div className="absolute left-[50%] h-8 w-24 bg-orange-400 rounded shadow-sm border border-orange-300"></div>
                 </div>
            </div>

            {/* Playhead */}
            <div className="absolute top-0 bottom-0 w-px bg-primary left-[35%] z-10">
                <div className="w-3 h-3 bg-primary rounded-full -ml-[5px] -mt-1"></div>
            </div>

        </div>
    );
};

export default Timeline;
