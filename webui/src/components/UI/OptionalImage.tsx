import { FC, useEffect, useState } from "react"

type OptionalImageProps = {
    src?: string
    alt: string
    width?: number
    height?: number
}

// taken from https://dev.to/know_dhruv/react-handle-image-loading-error-gracefully-using-custom-hook-21c2
const useImageError = () => {
    const [el, setEl] = useState<any>(null); // contains image reference
    const [error, setError] = useState(false); // contains error flag

    const _handleError = () => { setError(true); }  // set error
    const retry = () => { setError(false); } // set error false to img can re-render

    useEffect(() => {
        // use of error event of the image tag
        el?.addEventListener("error", _handleError);

        return () => {
            el?.removeEventListener("error", _handleError);
        }
    }, [el]);

    return [
        setEl, // set the image ref
        error, // error flag
        retry, // a func, which can be used to re-render image
        el // img ref(for special case which requires ref)
    ];
};


const OptionalImage: FC<OptionalImageProps> = ({ src, alt, width = 50, height = 50 }) => {

    const [setImg, hasError, retry, imgRef] = useImageError();

    if (hasError || (!src || src === '')) {
        return <label
            className="text-white bg-dark rounded-circle p-2 d-flex align-items-center justify-content-center"
            style={{ height: '50px', width: '50px' }}>
            {alt}
        </label>
    }
    return <img
        className="shadow-sm"
        ref={setImg}
        src={src}
        alt={alt}
        width={width}
        height={height} />
}

export default OptionalImage

