import { COLORS } from '../constants/theme';

const FILE_TYPE_URLS = {
  doc: (id) => `https://docs.google.com/document/d/${id}/preview`,
  sheet: (id) => `https://docs.google.com/spreadsheets/d/${id}/preview`,
  slide: (id) => `https://docs.google.com/presentation/d/${id}/preview`,
  form: (id) => `https://docs.google.com/forms/d/${id}/viewform?embedded=true`,
  pdf: (id) => `https://drive.google.com/file/d/${id}/preview`,
  file: (id) => `https://drive.google.com/file/d/${id}/preview`,
};

export default function GoogleDocEmbed({ fileId, fileType = 'doc', title, height = 600 }) {
  const urlFn = FILE_TYPE_URLS[fileType] || FILE_TYPE_URLS.file;
  const src = urlFn(fileId);

  return (
    <div style={{ marginBottom: 20 }}>
      {title && (
        <h4 style={{
          fontSize: 14, fontWeight: 700, color: COLORS.darkSlate,
          fontFamily: "'DM Sans', sans-serif", marginBottom: 8,
        }}>{title}</h4>
      )}
      <iframe
        src={src}
        title={title || 'Embedded Google File'}
        style={{
          width: '100%', height, border: 'none', borderRadius: 8,
          background: COLORS.white,
          boxShadow: `0 2px 8px ${COLORS.navy}08`,
        }}
        allow="autoplay"
      />
    </div>
  );
}
