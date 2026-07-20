import React from 'react';
import { CollaborationMessage } from './collaboration/CollaborationMessage';
import './DemoChatBubble.css';

const renderInlineContent = (text, boldPart) => {
  if (!text) return null;

  const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const patterns = [];

  if (boldPart) {
    patterns.push({ regex: new RegExp(escapeRegex(boldPart), 'g'), tag: 'strong' });
  }

  patterns.push({ regex: /\*\*([^*]+)\*\*/g, tag: 'strong' });
  patterns.push({ regex: /`([^`]+)`/g, tag: 'code' });

  const segments = [];
  let remaining = text;

  while (remaining) {
    let nextIndex = remaining.length;
    let matched = null;

    patterns.forEach((pattern) => {
      const match = pattern.regex.exec(remaining);
      if (match && match.index < nextIndex) {
        nextIndex = match.index;
        matched = { ...pattern, match, value: match[1] || match[0] };
      }
      pattern.regex.lastIndex = 0;
    });

    if (!matched) {
      segments.push(remaining);
      break;
    }

    if (nextIndex > 0) {
      segments.push(remaining.slice(0, nextIndex));
    }

    if (matched.tag === 'strong') {
      segments.push(<strong key={segments.length}>{matched.value}</strong>);
    } else {
      segments.push(<code key={segments.length}>{matched.value}</code>);
    }

    remaining = remaining.slice(nextIndex + matched.match[0].length);
  }

  return segments;
};

const renderMarkdownContent = (text, boldPart) => {
  const lines = String(text || '').split(/\n{2,}/).filter(Boolean);

  return (
    <div className="bubble-markdown">
      {lines.map((block, blockIndex) => {
        const blockLines = block.split('\n');
        const firstLine = blockLines[0]?.trim() || '';

        if (firstLine.startsWith('```')) {
          const codeLines = blockLines.slice(1).filter((line) => !line.startsWith('```'));
          return (
            <pre key={blockIndex} className="markdown-code-block">
              <code>{codeLines.join('\n')}</code>
            </pre>
          );
        }

        if (firstLine.startsWith('>')) {
          return (
            <blockquote key={blockIndex} className="markdown-quote">
              {blockLines.map((line, lineIndex) => (
                <div key={lineIndex}>{renderInlineContent(line.replace(/^>\s?/, ''), boldPart)}</div>
              ))}
            </blockquote>
          );
        }

        if (/^#{1,3}\s+/.test(firstLine)) {
          const level = firstLine.match(/^#+/)[0].length;
          const headingText = firstLine.replace(/^#{1,3}\s+/, '');
          const HeadingTag = `h${Math.min(level, 3)}`;
          return <HeadingTag key={blockIndex} className={`markdown-heading h${Math.min(level, 3)}`}>{renderInlineContent(headingText, boldPart)}</HeadingTag>;
        }

        const listItems = blockLines.filter((line) => /^\s*([-*]|\d+\.)\s+/.test(line));
        if (listItems.length > 0) {
          const isOrdered = listItems.some((line) => /^\s*\d+\.\s+/.test(line));
          const ListTag = isOrdered ? 'ol' : 'ul';
          return (
            <ListTag key={blockIndex} className="markdown-list">
              {listItems.map((line, lineIndex) => {
                const content = line.replace(/^\s*(?:[-*]|\d+\.)\s+/, '');
                return <li key={lineIndex}>{renderInlineContent(content, boldPart)}</li>;
              })}
            </ListTag>
          );
        }

        return (
          <p key={blockIndex} className="markdown-paragraph">
            {renderInlineContent(firstLine, boldPart)}
          </p>
        );
      })}
    </div>
  );
};

export const DemoChatBubble = ({ text, isEva, boldPart, userInitial = 'A', collaborationData = null, onSelectTimeSlot = null }) => {
  return (
    <div className={`chat-bubble-row ${isEva ? 'eva' : 'user'}`}>
      {isEva && (
        <div className="avatar avatar-eva font-body">
          <span>E</span>
        </div>
      )}
      
      <div className="bubble-content">
        {renderMarkdownContent(text, boldPart)}
        {isEva && collaborationData && (
          <CollaborationMessage 
            data={collaborationData} 
            onSelectTimeSlot={onSelectTimeSlot}
          />
        )}
      </div>

      {!isEva && (
        <div className="avatar avatar-user font-body">
          <span>{userInitial}</span>
        </div>
      )}
    </div>
  );
};

export default DemoChatBubble;
