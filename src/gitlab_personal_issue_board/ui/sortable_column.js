import '/js/Sortable.min.js'

export default {
    template: `
    <div>
      <slot></slot>
    </div>
  `,
    props: {
        group: String,
    },
    mounted() {
        this.makesortable();
    },
    methods: {
        makesortable() {
            if (this.group === 'None') {
                this.group = this.$el.id;
            }
            Sortable.create(this.$el, {
                group: this.group,
                animation: 150,
                handle: ".drop_handle",
                ghostClass: 'opacity-50',
                onEnd: (evt) => this.$emit("item-drop", {
                    parent: parseInt(this.$el.id.slice(1)),
                    id: parseInt(evt.item.id.slice(1)),
                    version: '1',
                    new_index: evt.newIndex,
                    new_list: parseInt(evt.to.id.slice(1)),
                    old_list: parseInt(evt.from.id.slice(1)),
                    event: evt,
                }),
            });
        },
    },
};
