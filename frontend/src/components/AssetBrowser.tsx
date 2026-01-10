import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Loader } from 'lucide-react';

interface ClipMetadata {
    filename: string;
    timestamp: number;
    latent_path: string;
}

const AssetBrowser: React.FC = () => {
    const [assets, setAssets] = useState<Record<string, ClipMetadata[]>>({});
    const [loading, setLoading] = useState(false);
    const [ingesting, setIngesting] = useState(false);

    const fetchAssets = async () => {
        setLoading(true);
        try {
            const res = await axios.get('http://localhost:8000/assets');
            if (res.data && res.data.assets) {
                setAssets(res.data.assets);
            }
        } catch (e) {
            console.error("Failed to fetch assets", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAssets();
    }, []);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files?.[0]) return;
        setIngesting(true);
        const formData = new FormData();
        formData.append('file', e.target.files[0]);

        try {
            await axios.post('http://localhost:8000/ingest', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            // Refresh
            await fetchAssets();
        } catch (error) {
            console.error(error);
            alert("Ingest failed");
        } finally {
            setIngesting(false);
        }
    };

    return (
        <div className="flex-1 overflow-y-auto p-2 scrollbar-hide">
             {/* Upload Button */}
             <div className="mb-4">
                <label className={`flex flex-col items-center justify-center w-full h-12 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer transition-colors ${ingesting ? 'bg-gray-100 cursor-not-allowed' : 'hover:border-primary hover:bg-gray-50'}`}>
                    {ingesting ? (
                         <span className="text-xs text-primary flex items-center gap-2"><Loader className="animate-spin" size={12}/> Processing...</span>
                    ) : (
                         <>
                            <span className="text-xs text-gray-500">Drop Video or Click</span>
                            <input type="file" className="hidden" accept="video/*" onChange={handleUpload} disabled={ingesting} />
                         </>
                    )}
                </label>
             </div>

             {loading && Object.keys(assets).length === 0 ? (
                 <div className="text-center text-xs text-gray-400 mt-4">Loading assets...</div>
             ) : (
                 <div className="grid grid-cols-2 gap-2">
                     {Object.keys(assets).map(filename => (
                         <div key={filename} className="relative aspect-video bg-gray-200 rounded overflow-hidden shadow-sm group">
                             <div className="absolute inset-0 flex items-center justify-center text-[10px] text-gray-500 break-all p-1 text-center bg-gray-200">
                                 {filename}
                             </div>
                             <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[9px] p-1 truncate">
                                 {assets[filename].length} clips
                             </div>
                         </div>
                     ))}
                 </div>
             )}
        </div>
    );
};

export default AssetBrowser;
