// The blog's version of django-prose's editor.js (2.1.0, MIT, withlogicco/django-prose).
// Files dropped into the editor are uploaded the same way, but an upload the server refuses
// (too big, signed out...) no longer stays in the post as a picture that never arrives:
// prose's script only handles a 201 answer, and Trix leaves a pending attachment out of the
// saved post without a word. Files over the server's limit are refused before uploading.
(function () {
  const MAX_BYTES = 30 * 1024 * 1024; // jiri_one.pictures.UPLOAD_MAX_BYTES

  function fail(attachment, message) {
    attachment.remove();
    window.alert(message);
  }

  function upload(host, attachment) {
    const data = new FormData();
    data.append("file", attachment.file);
    data.append("Content-Type", attachment.file.type);
    data.append("csrfmiddlewaretoken", document.querySelector("input[name=csrfmiddlewaretoken]").value);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", host, true);
    xhr.upload.addEventListener("progress", function (event) {
      attachment.setUploadProgress((event.loaded / event.total) * 100);
    });
    xhr.addEventListener("load", function () {
      if (xhr.status === 201) {
        const url = JSON.parse(xhr.response).url;
        attachment.setAttributes({ url: url, href: url });
        return;
      }
      let message = "Soubor " + attachment.file.name + " se nenahrál (HTTP " + xhr.status + ").";
      try {
        message = JSON.parse(xhr.response).error || message;
      } catch (error) {
        // not JSON, e.g. the login page after the session ran out
      }
      fail(attachment, message);
    });
    xhr.addEventListener("error", function () {
      fail(attachment, "Soubor " + attachment.file.name + " se nenahrál, server neodpověděl.");
    });
    xhr.send(data);
  }

  function initializeEditors() {
    document.querySelectorAll(".django-prose-editor:not(.initialized)").forEach(function (editor) {
      editor.addEventListener("trix-file-accept", function (event) {
        if (event.file && event.file.size > MAX_BYTES) {
          event.preventDefault();
          window.alert("Soubor " + event.file.name + " je větší než 30 MB, ten editor nenahraje.");
        }
      });
      editor.addEventListener("trix-attachment-add", function (event) {
        if (event.attachment.file) {
          upload(editor.dataset.uploadAttachmentUrl, event.attachment);
        }
      });
      editor.classList.add("initialized");
    });
  }

  // https://github.com/withlogicco/django-prose/issues/100
  function patchTrixEditorWithNameSetter() {
    Object.defineProperty(window.Trix.elements.TrixEditorElement.prototype, "name", {
      get() {
        return this.inputElement?.name;
      },
      set(value) {
        this.inputElement.name = value;
      },
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initializeEditors();
    patchTrixEditorWithNameSetter();
  });

  window.djangoProse = window.djangoProse || {};
  window.djangoProse.initializeEditors = initializeEditors;
})();
