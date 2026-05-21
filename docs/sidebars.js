// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'introduction',
    {
      type: 'category',
      label: 'Get started',
      link: { type: 'doc', id: 'get-started/index' },
      items: ['get-started/deploy'],
    },
    {
      type: 'category',
      label: 'How-to guides',
      link: { type: 'doc', id: 'how-tos/index' },
      items: [
        'how-tos/use',
        'how-tos/troubleshoot',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      link: { type: 'doc', id: 'references/index' },
      items: [
        'references/values',
        'references/architecture',
      ],
    },
  ],
};

module.exports = sidebars;
