import { FC, useEffect, useState } from "react"

type OptionalImageProps = {
    src: string
    alt: string
}

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


const OptionalImage: FC<OptionalImageProps> = ({ src, alt }) => {

    const [setImg, hasError, retry, imgRef] = useImageError();

    if (hasError)
        return <label className="text-white bg-dark rounded-circle p-2 align-middle" style={{ height: '40px', width: '40px' }}>{alt}</label>
    return <img className="shadow-sm" ref={setImg} src={src} alt={alt} />
}

export default OptionalImage

